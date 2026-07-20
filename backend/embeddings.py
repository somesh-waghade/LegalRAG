import requests
from typing import List
import os

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

# Optional Hugging Face token from environment variables to increase rate limits
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

def _query_hf_api(payload: dict) -> list:
    headers = {
        "X-Wait-For-Model": "true"
    }
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    
    # Try up to 3 times
    for attempt in range(3):
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            # Model is still loading despite X-Wait-For-Model header, wait and retry
            import time
            time.sleep(10)
            continue
        else:
            raise Exception(f"Hugging Face Inference API error ({response.status_code}): {response.text}")
    raise Exception("Hugging Face model failed to load in time.")


def _pool_embeddings(embeddings: list) -> List[List[float]]:
    """
    Hugging Face Inference API sometimes returns 3D lists [batch, seq_len, 384]
    for feature-extraction. This function pools them (mean pooling) into 2D [batch, 384].
    """
    if not isinstance(embeddings, list) or len(embeddings) == 0:
        return []

    # If it's already a 2D list of floats (batch, 384), return as is
    if isinstance(embeddings[0], list) and not isinstance(embeddings[0][0], list):
        return embeddings

    # If it's a 3D list (batch, seq_len, 384), perform mean pooling
    if isinstance(embeddings[0], list) and isinstance(embeddings[0][0], list):
        pooled = []
        for sentence_tokens in embeddings:
            seq_len = len(sentence_tokens)
            if seq_len == 0:
                pooled.append([0.0] * 384)
                continue
            
            dim = len(sentence_tokens[0])
            sum_vector = [0.0] * dim
            for token_vec in sentence_tokens:
                for idx in range(min(dim, len(token_vec))):
                    sum_vector[idx] += token_vec[idx]
            
            mean_vector = [val / seq_len for val in sum_vector]
            pooled.append(mean_vector)
        return pooled

    # If it's a 1D list (384), wrap it in a list
    if not isinstance(embeddings[0], list):
        return [embeddings]

    return embeddings


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings using Hugging Face Inference API.
    """
    if not texts:
        return []
    raw_embeddings = _query_hf_api({"inputs": texts})
    return _pool_embeddings(raw_embeddings)


def embed_query(query: str) -> List[float]:
    """
    Generate a single embedding for a search query.
    """
    raw_embeddings = _query_hf_api({"inputs": [query]})
    pooled = _pool_embeddings(raw_embeddings)
    if pooled and len(pooled) > 0:
        return pooled[0]
    raise ValueError("Unexpected response format from Hugging Face API.")


def get_embedding_dimension() -> int:
    """Return the dimensionality of all-MiniLM-L6-v2 (384)."""
    return 384

