"""
retriever.py - lightweight JSON vector store for LegalRAG demos.

This avoids ChromaDB's native SQLite/runtime issues on free Render instances
while keeping the same add/query/delete interface used by the RAG pipeline.
"""

import json
import math
import os
from typing import Any, Dict, List


VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db")
STORE_FILE = os.path.join(VECTOR_DB_PATH, "session_docs.json")


def _load_store() -> List[Dict[str, Any]]:
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    if not os.path.exists(STORE_FILE):
        return []

    with open(STORE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    if isinstance(data, list):
        return data
    return []


def _save_store(records: List[Dict[str, Any]]) -> None:
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    temp_file = f"{STORE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(records, f)
    os.replace(temp_file, STORE_FILE)


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right:
        return 0.0

    size = min(len(left), len(right))
    dot = sum(left[i] * right[i] for i in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def add_documents(
    doc_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Store document chunks and their embeddings in the local JSON vector store.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(f"Chunk/embedding count mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings")

    records = [record for record in _load_store() if record.get("doc_id") != doc_id]
    for chunk, embedding in zip(chunks, embeddings):
        records.append(
            {
                "id": f"{doc_id}_{chunk['chunk_id']}",
                "doc_id": doc_id,
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_num": chunk["page_num"],
                "source_filename": chunk["source_filename"],
                "embedding": embedding,
            }
        )

    _save_store(records)
    print(f"[Retriever] Stored {len(chunks)} chunks for doc_id={doc_id} in JSON vector store.")
    return len(chunks)


def query_documents(
    query_embedding: List[float],
    n_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks across all uploaded documents.
    """
    records = _load_store()
    if not records:
        return []

    scored = []
    for record in records:
        score = _cosine_similarity(query_embedding, record.get("embedding", []))
        scored.append((score, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    retrieved = []
    for score, record in scored[: max(1, n_results)]:
        retrieved.append(
            {
                "text": record["text"],
                "page_num": record["page_num"],
                "source_filename": record["source_filename"],
                "distance": 1.0 - score,
            }
        )

    return retrieved


def delete_document(doc_id: str) -> bool:
    """
    Delete a specific document's chunks from the local JSON vector store.
    """
    records = _load_store()
    filtered = [record for record in records if record.get("doc_id") != doc_id]
    _save_store(filtered)
    print(f"[Retriever] Deleted chunks for doc_id={doc_id} from JSON vector store.")
    return True


def clear_all_documents() -> bool:
    """
    Delete all session vectors.
    """
    _save_store([])
    print("[Retriever] Cleared JSON vector store.")
    return True
