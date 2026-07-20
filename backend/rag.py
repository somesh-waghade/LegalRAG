"""
rag.py – Core RAG pipeline orchestration for LegalRAG.

Handles:
  - Document ingestion (PDF → chunks → embeddings → vector DB)
  - Question answering (query → retrieve → LLM → answer + citations)
  - Document summarization (all chunks → LLM → summary)
"""

import os
from groq import Groq
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple

from backend.pdf_reader import process_pdf
from backend.embeddings import embed_texts, embed_query
from backend.retriever import (
    add_documents,
    query_documents,
)

load_dotenv(override=True)

# ─── Groq Configuration ──────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.1-8b-instant"

_client: Groq | None = None

def _get_client() -> Groq:
    """Return a cached Groq Client instance."""
    global _client
    # Always reload env in case it changed while the app was running
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Please add it to your .env file."
        )
    if _client is None:
        _client = Groq(api_key=api_key)
    return _client


def _generate_with_retry(prompt: str, max_retries: int = 3) -> str:
    """
    Call Groq API with automatic retry on rate-limit (429) errors.
    """
    import time
    client = _get_client()
    delay = 5  # seconds between retries
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful legal AI assistant. You answer based ONLY on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                wait = delay * (attempt + 1)
                print(f"[RAG] Rate limit hit, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise

    raise last_error

def ingest_document(file_path: str, doc_id: str) -> Dict[str, Any]:
    """
    Full ingestion pipeline: PDF → extract → chunk → embed → store.

    Args:
        file_path: Path to the uploaded PDF file.
        doc_id: UUID assigned to this document.

    Returns:
        Dict with ingestion stats: num_pages, num_chunks, filename.
    """
    print(f"[RAG] Ingesting document: {file_path}")
    filename = os.path.basename(file_path)
    ingestion_warnings = []

    # Step 1: Extract text and chunk
    try:
        chunks = process_pdf(file_path)
    except Exception as error:
        ingestion_warnings.append(f"PDF extraction failed: {error}")
        print(f"[RAG] PDF extraction failed, using placeholder chunk: {error}")
        chunks = []

    if not chunks:
        ingestion_warnings.append("No extractable PDF text was found.")
        chunks = [
            {
                "chunk_id": 0,
                "text": (
                    f"The file '{filename}' was uploaded, but no searchable text could be extracted. "
                    "This usually happens with scanned PDFs or image-only documents."
                ),
                "page_num": 1,
                "source_filename": filename,
            }
        ]

    num_pages = max(c["page_num"] for c in chunks)

    # Step 2: Generate embeddings
    texts = [chunk["text"] for chunk in chunks]
    try:
        embeddings = embed_texts(texts)
    except Exception as error:
        ingestion_warnings.append(f"Configured embedding provider failed: {error}")
        print(f"[RAG] Embedding provider failed, retrying with local embeddings: {error}")
        previous_provider = os.environ.get("EMBEDDING_PROVIDER")
        os.environ["EMBEDDING_PROVIDER"] = "local"
        try:
            embeddings = embed_texts(texts)
        finally:
            if previous_provider is None:
                os.environ.pop("EMBEDDING_PROVIDER", None)
            else:
                os.environ["EMBEDDING_PROVIDER"] = previous_provider

    # Step 3: Store in vector database
    num_stored = add_documents(doc_id, chunks, embeddings)

    print(f"[RAG] Ingestion complete: {num_stored} chunks from {num_pages} pages.")
    if ingestion_warnings:
        print(f"[RAG] Ingestion warnings for {filename}: {' | '.join(ingestion_warnings)}")

    return {
        "filename": filename,
        "num_pages": num_pages,
        "num_chunks": num_stored,
        "doc_id": doc_id,
    }


# ─── Question Answering ────────────────────────────────────────────────────────

def answer_question(
    question: str,
    n_results: int = 5,
) -> Dict[str, Any]:
    """
    Answer a user's question using the RAG pipeline across ALL uploaded documents.
    """
    # Step 1: Embed question
    query_embedding = embed_query(question)

    # Step 2: Retrieve relevant chunks
    retrieved = query_documents(
        query_embedding=query_embedding,
        n_results=n_results,
    )

    if not retrieved:
        return {
            "answer": "I don't have any uploaded documents to search through. Please upload a document first.",
            "sources": [],
        }

    # Step 3: Format context
    context_parts = []
    for i, chunk in enumerate(retrieved):
        context_parts.append(
            f"--- Source [{i+1}] (File: {chunk['source_filename']}, Page: {chunk['page_num']}) ---\n"
            f"{chunk['text']}\n"
        )
    context_text = "\n".join(context_parts)

    # Step 4: Construct prompt
    prompt = f"""You are a helpful, professional legal AI assistant.
Answer the user's question based ONLY on the provided context.
If the context does not contain the answer, say "I cannot find the answer to this question in the uploaded documents."
Do not use outside knowledge. Cite your sources by referring to the filename and page number.

CONTEXT:
{context_text}

USER QUESTION:
{question}

ANSWER:"""

    # Step 5: Call API with retry
    answer_text = _generate_with_retry(prompt)

    # Step 6: Build source citations
    sources = []
    seen = set()
    for chunk in retrieved:
        key = (chunk["source_filename"], chunk["page_num"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "source_filename": chunk["source_filename"],
                "page_num": chunk["page_num"],
                "excerpt": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            })

    return {
        "answer": answer_text,
        "sources": sources,
    }
