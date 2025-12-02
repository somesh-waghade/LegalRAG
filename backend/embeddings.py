"""
embeddings.py – Generate text embeddings using sentence-transformers.

Uses the lightweight all-MiniLM-L6-v2 model which provides a good balance
between embedding quality and inference speed for semantic search tasks.
"""

from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np


# Singleton model instance – loaded once and reused across requests
_model: SentenceTransformer | None = None

MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (singleton pattern)."""
    global _model
    if _model is None:
        print(f"[Embeddings] Loading model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        print("[Embeddings] Model loaded successfully.")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (each vector is a list of floats).
    """
    model = _get_model()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalize for cosine similarity
    )
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    """
    Generate a single embedding for a search query.

    Args:
        query: The user's question or search text.

    Returns:
        A single embedding vector as a list of floats.
    """
    model = _get_model()
    embedding = model.encode(
        query,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embedding.tolist()


def get_embedding_dimension() -> int:
    """Return the dimensionality of the embedding model's output."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()
