"""
Search Agent — DuckDuckGo + optional Tavily (free tier) search.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse
from dotenv import load_dotenv

from utils.config import get_secret
from utils.request_context import get_tavily_api_key

load_dotenv()

_MAX_RESULTS = 10


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    domain: str
    source: str  # "duckduckgo" | "tavily"


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lstrip("www.")
    except Exception:
        return url


# ──────────────────────────────────────────────────────────────────────
# DuckDuckGo
# ──────────────────────────────────────────────────────────────────────
def _ddg_search(query: str, max_results: int) -> list[SearchResult]:
    try:
        from ddgs import DDGS

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                url   = r.get("href") or r.get("url", "")
                title = r.get("title", "")
                body  = r.get("body", "")
                print("Duck-Duck-Go", url)
                if url:
                    results.append(
                        SearchResult(
                            url=url,
                            title=title,
                            snippet=body,
                            domain=_domain(url),
                            source="duckduckgo",
                        )
                    )
        return results
    except Exception as e:
        print(f"[SearchAgent] DuckDuckGo error: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────
# Tavily (optional)
# ──────────────────────────────────────────────────────────────────────
def _tavily_search(query: str, max_results: int) -> list[SearchResult]:
    tavily_key = get_tavily_api_key() or get_secret("TAVILY_API_KEY")
    if not tavily_key:
        return []
    try:
        from tavily import TavilyClient

        client  = TavilyClient(api_key=tavily_key)
        resp    = client.search(query, max_results=max_results)
        results = []
        for r in resp.get("results", []):
            url = r.get("url", "")
            print("Tavily Search", url)
            results.append(
                SearchResult(
                    url=url,
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    domain=_domain(url),
                    source="tavily",
                )
            )
        return results
    except Exception as e:
        print(f"[SearchAgent] Tavily error: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────
def run_search_agent(
    search_queries: list[str],
    max_results_per_query: int | None = None,
) -> list[SearchResult]:
    """
    Search DuckDuckGo (+ Tavily if configured) for each query.
    De-duplicates by URL and returns a flat list.
    """
    per_q = max_results_per_query or max(4, _MAX_RESULTS // len(search_queries))
    seen: set[str] = set()
    all_results: list[SearchResult] = []

    for query in search_queries:
        batch: list[SearchResult] = []
        batch.extend(_tavily_search(query, per_q))     # Tavily first (better)
        batch.extend(_ddg_search(query, per_q))         # DDG as fallback/supplement

        for r in batch:
            if r.url not in seen and r.url:
                seen.add(r.url)
                all_results.append(r)

    return all_results[:_MAX_RESULTS * 2]  # cap total
