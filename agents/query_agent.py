"""
Query Agent — understands & expands the user query into a structured plan.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from utils.llm_client import get_llm_client


@dataclass
class QueryPlan:
    original_query: str
    refined_query: str
    sub_queries: list[str]
    keywords: list[str]
    intent: str                   # e.g. "factual", "comparative", "how-to"
    search_queries: list[str]     # queries ready to pass to search agent


_SYSTEM = """You are an expert research strategist. When given a user query you:
1. Refine the query for precision
2. Break it into 2-4 targeted sub-questions
3. Extract important keywords / entities
4. Identify the query intent
5. Generate 3-5 diverse search engine queries to maximise coverage

Respond ONLY with valid JSON matching this schema:
{
  "refined_query": "...",
  "sub_queries": ["...", "..."],
  "keywords": ["...", "..."],
  "intent": "factual|comparative|how-to|exploratory",
  "search_queries": ["...", "..."]
}"""


def run_query_agent(query: str) -> QueryPlan:
    """Expand and structure the user query."""
    llm = get_llm_client()
    raw = llm.chat(
        messages=[{"role": "user", "content": f"Query: {query}"}],
        system=_SYSTEM,
        temperature=0.2,
        max_tokens=1024,
    )

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: minimal plan
        data = {
            "refined_query": query,
            "sub_queries": [query],
            "keywords": query.split()[:5],
            "intent": "factual",
            "search_queries": [query],
        }

    return QueryPlan(
        original_query=query,
        refined_query=data.get("refined_query", query),
        sub_queries=data.get("sub_queries", [query]),
        keywords=data.get("keywords", []),
        intent=data.get("intent", "factual"),
        search_queries=data.get("search_queries", [query]),
    )
