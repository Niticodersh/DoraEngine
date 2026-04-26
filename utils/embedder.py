"""
Embedder — singleton fastembed model for chunk embedding.

Uses ONNX runtime instead of PyTorch to keep memory footprint under ~150MB.
Imports are still deferred to avoid slowing down FastAPI startup.
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

warnings.filterwarnings("ignore", category=ImportWarning, module="transformers.*")

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as _cosine_sim

if TYPE_CHECKING:
    from fastembed import TextEmbedding

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_embedder_instance: "TextEmbedding | None" = None


def _get_model() -> "TextEmbedding":
    """Lazy-load the embedding model on first call."""
    from fastembed import TextEmbedding  # noqa: PLC0415
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = TextEmbedding(_MODEL_NAME)
    return _embedder_instance


def embed(texts: list[str]) -> np.ndarray:
    """
    Returns a 2-D numpy array of shape (len(texts), embedding_dim).
    """
    model = _get_model()
    # fastembed returns a generator of numpy arrays, convert to a single 2D array
    return np.array(list(model.embed(texts)))


def embed_single(text: str) -> np.ndarray:
    """Embed a single string -> 1-D numpy array."""
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
