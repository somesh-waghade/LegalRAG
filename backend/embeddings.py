import requests
from typing import List
import os

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

# Optional Hugging Face token from environment variables to increase rate limits
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

def _query_hf_api(payload: dict) -> list:
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    
    # Try up to 3 times in case the model is loading
    for attempt in range(3):
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            # Model is loading, wait and retry
            import time
            time.sleep(5)
            continue
        else:
            raise Exception(f"Hugging Face Inference API error ({response.status_code}): {response.text}")
    raise Exception("Hugging Face model failed to load in time.")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings using Hugging Face Inference API.
    """
    if not texts:
        return []
    embeddings = _query_hf_api({"inputs": texts})
    # HF sometimes returns a flat list if there's only 1 text, normalize to list of lists
    if isinstance(embeddings, list) and len(embeddings) > 0 and not isinstance(embeddings[0], list):
        return [embeddings]
    return embeddings


def embed_query(query: str) -> List[float]:
    """
    Generate a single embedding for a search query.
    """
    embeddings = _query_hf_api({"inputs": [query]})
    if isinstance(embeddings, list) and len(embeddings) > 0:
        if isinstance(embeddings[0], list):
            return embeddings[0]
        return embeddings
    raise ValueError("Unexpected response format from Hugging Face API.")


def get_embedding_dimension() -> int:
    """Return the dimensionality of all-MiniLM-L6-v2 (384)."""
    return 384

