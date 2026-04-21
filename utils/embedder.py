"""
Embedder — singleton sentence-transformers model for chunk embedding.
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=ImportWarning, module="transformers.*")

import numpy as np
# from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity as _cosine_sim

_MODEL_NAME = "all-MiniLM-L6-v2"
_embedder_instance: SentenceTransformer | None = None


def _get_model():
    from sentence_transformers import SentenceTransformer
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = SentenceTransformer(_MODEL_NAME)
    return _embedder_instance


def embed(texts: list[str]) -> np.ndarray:
    """
    Returns a 2-D numpy array of shape (len(texts), embedding_dim).
    """
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def embed_single(text: str) -> np.ndarray:
    """Embed a single string → 1-D numpy array."""
    return embed([text])[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Scalar cosine similarity between two 1-D vectors."""
    return float(_cosine_sim(a.reshape(1, -1), b.reshape(1, -1))[0, 0])


def batch_cosine_similarity(
    query_vec: np.ndarray, matrix: np.ndarray
) -> np.ndarray:
    """
    Compute cosine similarity between a single query vector and a matrix
    of vectors. Returns 1-D array of scores.
    """
    return _cosine_sim(query_vec.reshape(1, -1), matrix)[0]
