"""
Chunker — sliding window text chunker with token-based splitting.
"""
from __future__ import annotations

import re


def _simple_tokenize(text: str) -> list[str]:
    """Naive whitespace tokenizer — good enough for chunking estimates."""
    return text.split()


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    Split `text` into overlapping chunks by approximate token count.

    Args:
        text:       The raw text to chunk.
        chunk_size: Target number of tokens per chunk.
        overlap:    Number of tokens to overlap between consecutive chunks.

    Returns:
        List of text chunk strings.
    """
    # Collapse excessive whitespace / newlines
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    tokens = _simple_tokenize(text)

    if len(tokens) <= chunk_size:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(" ".join(chunk_tokens))
        if end == len(tokens):
            break
        start += chunk_size - overlap  # slide forward

    return chunks


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[dict]:
    """
    Chunk a list of document dicts, each with at least a 'content' key.
    Returns a flat list of chunk dicts with inherited metadata + chunk_index.
    """
    chunks: list[dict] = []
    for doc in documents:
        content = doc.get("content", "")
        if not content or not content.strip():
            continue
        text_chunks = chunk_text(content, chunk_size, overlap)
        for i, chunk in enumerate(text_chunks):
            chunks.append(
                {
                    **{k: v for k, v in doc.items() if k != "content"},
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                }
            )
    return chunks
