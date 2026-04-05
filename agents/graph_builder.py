"""
Graph Builder — builds a NetworkX knowledge graph from scraped pages.

Nodes: text chunks with embeddings
Edges:
  - sequential  (same source, consecutive chunks)
  - semantic    (cosine similarity > threshold)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import networkx as nx
import numpy as np
from dotenv import load_dotenv

from utils.chunker import chunk_documents
from utils.embedder import embed, batch_cosine_similarity

load_dotenv()

_SIM_THRESHOLD = 0.65
_CHUNK_SIZE    = 500
_CHUNK_OVERLAP = 100


@dataclass
class GraphState:
    graph: nx.Graph
    node_ids: list[str]          # ordered list of node IDs
    embeddings: np.ndarray       # shape (N, dim)
    chunks: list[dict]           # ordered, mirrors node_ids


def _make_node_id(doc_index: int, chunk_index: int) -> str:
    return f"doc{doc_index}_chunk{chunk_index}"


def build_graph(scraped_pages: list) -> GraphState:
    """
    Build a NetworkX graph from a list of ScrapedPage objects.

    Args:
        scraped_pages: List of ScrapedPage (from scraper_agent).

    Returns:
        GraphState with the populated graph and index structures.
    """
    G = nx.Graph()

    # ── 1. Prepare documents ───────────────────────────────────────────
    docs = []
    for i, page in enumerate(scraped_pages):
        if not getattr(page, "success", False) or not page.content:
            continue
        docs.append(
            {
                "doc_index": i,
                "url":       page.url,
                "title":     page.title,
                "domain":    page.domain,
                "content":   page.content,
            }
        )

    if not docs:
        # Return empty graph
        dummy = np.zeros((0, 384))
        return GraphState(graph=G, node_ids=[], embeddings=dummy, chunks=[])

    # ── 2. Chunk ───────────────────────────────────────────────────────
    chunks = chunk_documents(docs, chunk_size=_CHUNK_SIZE, overlap=_CHUNK_OVERLAP)

    # ── 3. Embed ───────────────────────────────────────────────────────
    texts      = [c["content"] for c in chunks]
    embeddings = embed(texts)   # (N, dim)

    # ── 4. Add nodes ──────────────────────────────────────────────────
    node_ids: list[str] = []
    for idx, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        node_id = _make_node_id(chunk.get("doc_index", 0), chunk.get("chunk_index", idx))
        node_ids.append(node_id)
        G.add_node(
            node_id,
            content     = chunk["content"],
            url         = chunk.get("url", ""),
            title       = chunk.get("title", ""),
            domain      = chunk.get("domain", ""),
            chunk_index = chunk.get("chunk_index", 0),
            doc_index   = chunk.get("doc_index", 0),
        )

    # ── 5. Sequential edges (same doc, adjacent chunks) ───────────────
    prev_node: dict[int, str] = {}   # doc_index → last node_id

    for idx, chunk in enumerate(chunks):
        doc_idx   = chunk.get("doc_index", 0)
        node_id   = node_ids[idx]
        if doc_idx in prev_node:
            G.add_edge(
                prev_node[doc_idx], node_id,
                type="sequential", weight=0.9,
            )
        prev_node[doc_idx] = node_id

    # ── 6. Semantic edges ─────────────────────────────────────────────
    N = len(node_ids)
    # Batch similarity: for each node compute similarity to all others
    # Use vectorised approach to avoid O(N²) Python loops
    norm_emb = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
    sim_matrix = norm_emb @ norm_emb.T   # (N, N)

    for i in range(N):
        for j in range(i + 1, N):
            sim = float(sim_matrix[i, j])
            # Skip sequential (same doc, adjacent) — already added
            same_doc = chunks[i].get("doc_index") == chunks[j].get("doc_index")
            adj      = abs(chunks[i].get("chunk_index", 0) - chunks[j].get("chunk_index", 0)) == 1
            if same_doc and adj:
                continue
            if sim >= _SIM_THRESHOLD:
                G.add_edge(
                    node_ids[i], node_ids[j],
                    type="semantic", weight=round(sim, 4),
                )

    return GraphState(
        graph      = G,
        node_ids   = node_ids,
        embeddings = embeddings,
        chunks     = chunks,
    )
