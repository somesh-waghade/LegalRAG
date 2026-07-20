import hashlib
import math
import os
from typing import List


EMBEDDING_DIMENSION = 384
OPENAI_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
GEMINI_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
HF_MODEL_NAME = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_NAME}"


def _embedding_provider() -> str:
    configured = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
    if configured != "auto":
        return configured
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    if os.getenv("HF_TOKEN", "").strip():
        return "huggingface"
    return "local"


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict | list:
    import requests

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code >= 400:
        raise RuntimeError(f"API error ({response.status_code}): {response.text}")
    return response.json()


def _embed_with_openai(texts: List[str]) -> List[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    payload = {
        "model": OPENAI_MODEL,
        "input": texts,
        "dimensions": EMBEDDING_DIMENSION,
    }
    data = _post_json(
        "https://api.openai.com/v1/embeddings",
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload,
    )
    return [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])]


def _embed_with_gemini(texts: List[str], task_type: str) -> List[List[float]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    embeddings = []
    for text in texts:
        result = genai.embed_content(
            model=GEMINI_MODEL,
            content=text,
            task_type=task_type,
        )
        embeddings.append(result["embedding"])
    return embeddings


def _pool_hf_embeddings(embeddings: list) -> List[List[float]]:
    if not isinstance(embeddings, list) or len(embeddings) == 0:
        return []

    if isinstance(embeddings[0], list) and embeddings[0] and not isinstance(embeddings[0][0], list):
        return embeddings

    if isinstance(embeddings[0], list) and embeddings[0] and isinstance(embeddings[0][0], list):
        pooled = []
        for sentence_tokens in embeddings:
            if not sentence_tokens:
                pooled.append([0.0] * EMBEDDING_DIMENSION)
                continue

            dim = len(sentence_tokens[0])
            sum_vector = [0.0] * dim
            for token_vec in sentence_tokens:
                for idx in range(min(dim, len(token_vec))):
                    sum_vector[idx] += token_vec[idx]
            pooled.append([val / len(sentence_tokens) for val in sum_vector])
        return pooled

    if not isinstance(embeddings[0], list):
        return [embeddings]

    return embeddings


def _embed_with_huggingface(texts: List[str]) -> List[List[float]]:
    headers = {"X-Wait-For-Model": "true"}
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    last_error = None
    for _ in range(3):
        try:
            data = _post_json(HF_API_URL, headers, {"inputs": texts}, timeout=60)
            return _pool_hf_embeddings(data)
        except RuntimeError as error:
            last_error = error
            if "503" not in str(error):
                raise

    raise last_error or RuntimeError("Hugging Face embedding request failed.")


def _embed_locally(texts: List[str]) -> List[List[float]]:
    embeddings = []
    for text in texts:
        vector = [0.0] * EMBEDDING_DIMENSION
        tokens = text.lower().split()

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        embeddings.append(vector)

    return embeddings


def _normalize_dimensions(embeddings: List[List[float]]) -> List[List[float]]:
    normalized = []
    for embedding in embeddings:
        vector = list(embedding[:EMBEDDING_DIMENSION])
        if len(vector) < EMBEDDING_DIMENSION:
            vector.extend([0.0] * (EMBEDDING_DIMENSION - len(vector)))
        normalized.append(vector)
    return normalized


def _embed_texts_with_task(texts: List[str], gemini_task_type: str) -> List[List[float]]:
    """
    Generate embeddings using OpenAI, Hugging Face, or a local fallback.
    Set EMBEDDING_PROVIDER=openai, huggingface, or local to force a provider.
    """
    if not texts:
        return []

    provider = _embedding_provider()
    try:
        if provider == "openai":
            embeddings = _embed_with_openai(texts)
        elif provider == "gemini":
            embeddings = _embed_with_gemini(texts, gemini_task_type)
        elif provider == "huggingface":
            embeddings = _embed_with_huggingface(texts)
        elif provider == "local":
            embeddings = _embed_locally(texts)
        else:
            raise RuntimeError(f"Unsupported EMBEDDING_PROVIDER: {provider}")
    except Exception as error:
        if os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower() != "auto":
            raise
        print(f"[Embeddings] {provider} provider failed, using local fallback: {error}")
        embeddings = _embed_locally(texts)

    return _normalize_dimensions(embeddings)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate document embeddings using OpenAI, Gemini, Hugging Face, or a local fallback.
    Set EMBEDDING_PROVIDER=gemini, openai, huggingface, or local to force a provider.
    """
    return _embed_texts_with_task(texts, "retrieval_document")


def embed_query(query: str) -> List[float]:
    embeddings = _embed_texts_with_task([query], "retrieval_query")
    if embeddings:
        return embeddings[0]
    raise ValueError("Could not generate query embedding.")


def get_embedding_dimension() -> int:
    return EMBEDDING_DIMENSION
