"""
Ranking Agent — LLM-based relevance re-ranking of retrieved context chunks.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from utils.llm_client import get_llm_client
from agents.graph_rag import RetrievedContext


@dataclass
class RankedChunk:
    content:   str
    url:       str
    title:     str
    domain:    str
    score:     float
    relevance: float   # LLM-assigned relevance (0–1)
    reason:    str


_SYSTEM = """You are a relevance judge. Given a research query and a list of text chunks,
score each chunk's relevance to the query from 0.0 to 1.0.

Respond ONLY with a JSON array. Each element must be:
{"index": <int>, "relevance": <float 0-1>, "reason": "<one sentence>"}

Be strict: only high-quality, directly relevant chunks should score above 0.7."""


def run_ranking_agent(
    query: str,
    contexts: list[RetrievedContext],
    top_n: int = 12,
) -> list[RankedChunk]:
    """
    Re-rank retrieved chunks by LLM relevance score.
    Falls back to graph score ordering if LLM call fails.
    """
    if not contexts:
        return []

    # Pre-filter: only send top 20 by graph score to avoid huge prompts
    candidates = sorted(contexts, key=lambda x: x.score, reverse=True)[:20]

    # Build prompt
    chunks_text = "\n\n".join(
        f"[{i}] {c.content[:400]}" for i, c in enumerate(candidates)
    )
    prompt = f"Query: {query}\n\nChunks:\n{chunks_text}"

    llm    = get_llm_client()
    ranked = []

    try:
        raw = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=_SYSTEM,
            temperature=0.1,
            max_tokens=1024,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        scores_data = json.loads(raw)

        score_map: dict[int, tuple[float, str]] = {
            item["index"]: (item["relevance"], item.get("reason", ""))
            for item in scores_data
            if isinstance(item, dict)
        }

        for i, ctx in enumerate(candidates):
            rel, reason = score_map.get(i, (ctx.score, ""))
            ranked.append(
                RankedChunk(
                    content   = ctx.content,
                    url       = ctx.url,
                    title     = ctx.title,
                    domain    = ctx.domain,
                    score     = ctx.score,
                    relevance = float(rel),
                    reason    = reason,
                )
            )

        ranked.sort(key=lambda x: x.relevance, reverse=True)

    except Exception as e:
        # Fallback: use graph scores
        print(f"[RankingAgent] LLM re-rank failed ({e}), using graph scores.")
        for ctx in candidates:
            ranked.append(
                RankedChunk(
                    content   = ctx.content,
                    url       = ctx.url,
                    title     = ctx.title,
                    domain    = ctx.domain,
                    score     = ctx.score,
                    relevance = ctx.score,
                    reason    = "Graph score (LLM ranking unavailable)",
                )
            )
        ranked.sort(key=lambda x: x.relevance, reverse=True)

    # Deduplicate by first 80 chars of content
    seen: set[str] = set()
    deduped = []
    for chunk in ranked:
        key = chunk.content[:80]
        if key not in seen:
            seen.add(key)
            deduped.append(chunk)

    return deduped[:top_n]
