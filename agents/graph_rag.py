"""
Graph RAG Retriever — multi-hop retrieval over the knowledge graph.

Strategy:
  1. Embed the query
  2. Find top-K seed nodes by cosine similarity
  3. BFS-expand neighbors up to MAX_HOP_DEPTH hops
  4. Collect, score, and deduplicate context chunks
"""
from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass

import numpy as np
import networkx as nx

from utils.embedder import embed_single, batch_cosine_similarity
from agents.graph_builder import GraphState

load_env = __import__("dotenv").load_dotenv
load_env()

_TOP_K    = 8
_MAX_HOPS = 2


@dataclass
class RetrievedContext:
    node_id:   str
    content:   str
    url:       str
    title:     str
    domain:    str
    score:     float   # combined relevance score
    hop_depth: int     # 0 = seed, 1 = 1-hop neighbor, …


def retrieve(
    query: str,
    graph_state: GraphState,
    top_k: int = _TOP_K,
    max_hops: int = _MAX_HOPS,
) -> list[RetrievedContext]:
    """
    Multi-hop graph RAG retrieval.

    Returns a deduplicated, relevance-sorted list of RetrievedContext.
    """
    G          = graph_state.graph
    node_ids   = graph_state.node_ids
    embeddings = graph_state.embeddings

    if len(node_ids) == 0:
        return []

    # ── 1. Embed query ─────────────────────────────────────────────────
    q_vec  = embed_single(query)
    scores = batch_cosine_similarity(q_vec, embeddings)   # (N,)

    # ── 2. Top-K seed nodes ────────────────────────────────────────────
    top_k_actual = min(top_k, len(node_ids))
    seed_idxs    = np.argsort(scores)[::-1][:top_k_actual]

    visited:  dict[str, RetrievedContext] = {}
    frontier: deque[tuple[str, int, float]] = deque()

    for idx in seed_idxs:
        nid   = node_ids[idx]
        score = float(scores[idx])
        if nid not in visited:
            data = G.nodes[nid]
            visited[nid] = RetrievedContext(
                node_id   = nid,
                content   = data.get("content", ""),
                url       = data.get("url", ""),
                title     = data.get("title", ""),
                domain    = data.get("domain", ""),
                score     = score,
                hop_depth = 0,
            )
            if max_hops > 0:
                frontier.append((nid, 0, score))

    # ── 3. BFS neighbor expansion ─────────────────────────────────────
    while frontier:
        current_nid, depth, parent_score = frontier.popleft()
        if depth >= max_hops:
            continue

        for neighbor in G.neighbors(current_nid):
            if neighbor in visited:
                continue

            # Edge weight boosts propagation score
            edge_data    = G.edges[current_nid, neighbor]
            edge_weight  = edge_data.get("weight", 0.5)

            # Score decays with hop depth but is boosted by edge strength
            hop_score = parent_score * edge_weight * (0.7 ** (depth + 1))

            # Also add direct query similarity
            if neighbor in graph_state.node_ids:
                ni = graph_state.node_ids.index(neighbor)
                direct_sim = float(scores[ni])
                final_score = max(hop_score, direct_sim * 0.8)
            else:
                final_score = hop_score

            data = G.nodes[neighbor]
            visited[neighbor] = RetrievedContext(
                node_id   = neighbor,
                content   = data.get("content", ""),
                url       = data.get("url", ""),
                title     = data.get("title", ""),
                domain    = data.get("domain", ""),
                score     = final_score,
                hop_depth = depth + 1,
            )
            frontier.append((neighbor, depth + 1, final_score))

    # ── 4. Sort & return ──────────────────────────────────────────────
    results = sorted(visited.values(), key=lambda x: x.score, reverse=True)
    return results
