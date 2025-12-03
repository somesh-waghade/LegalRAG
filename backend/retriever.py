"""
retriever.py – ChromaDB vector store operations for LegalRAG.

Each document gets its own ChromaDB collection named by its doc_id (UUID).
This enables per-document or multi-document queries while keeping data isolated.
"""

import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any, Optional

# Persistent storage path
VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db")

# Singleton ChromaDB client
_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    """Lazy-initialize and return the ChromaDB persistent client."""
    global _client
    if _client is None:
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        print(f"[Retriever] ChromaDB initialized at: {VECTOR_DB_PATH}")
    return _client


def add_documents(
    doc_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Store document chunks and their embeddings in the unified session collection.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name="session_docs",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{doc_id}_{chunk['chunk_id']}" for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [
        {
            "page_num": chunk["page_num"],
            "source_filename": chunk["source_filename"],
            "chunk_id": chunk["chunk_id"],
            "doc_id": doc_id,
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"[Retriever] Stored {len(chunks)} chunks for doc_id={doc_id} into unified session.")
    return len(chunks)


def query_documents(
    query_embedding: List[float],
    n_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant chunks across all uploaded documents simultaneously.
    """
    client = _get_client()
    try:
        collection = client.get_collection(name="session_docs")
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []

    n_results = min(n_results, count)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    for i in range(len(results["documents"][0])):
        retrieved.append({
            "text": results["documents"][0][i],
            "page_num": results["metadatas"][0][i]["page_num"],
            "source_filename": results["metadatas"][0][i]["source_filename"],
            "distance": results["distances"][0][i],
        })

    return retrieved


def delete_document(doc_id: str) -> bool:
    """
    Delete a specific document's chunks from the unified session collection.
    """
    client = _get_client()
    try:
        collection = client.get_collection(name="session_docs")
        # ChromaDB allows deleting by metadata
        collection.delete(where={"doc_id": doc_id})
        print(f"[Retriever] Deleted chunks for doc_id={doc_id} from session collection.")
        return True
    except Exception:
        return False


def clear_all_documents() -> bool:
    """
    Delete the entire session collection from ChromaDB.
    """
    client = _get_client()
    try:
        client.delete_collection(name="session_docs")
        print("[Retriever] Cleared session collection.")
        return True
    except Exception:
        return False
