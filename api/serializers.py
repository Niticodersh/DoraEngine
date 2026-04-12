"""Serialization helpers for turning research objects into API payloads."""
from __future__ import annotations

from collections import Counter


def serialize_query_plan(plan) -> dict | None:
    if not plan:
        return None
    return {
        "original_query": plan.original_query,
        "refined_query": plan.refined_query,
        "sub_queries": plan.sub_queries,
        "keywords": plan.keywords,
        "intent": plan.intent,
        "search_queries": plan.search_queries,
    }


def serialize_search_result(result) -> dict:
    return {
        "url": result.url,
        "title": result.title,
        "snippet": result.snippet,
        "domain": result.domain,
        "source": result.source,
    }


def serialize_scraped_page(page) -> dict:
    return {
        "url": page.url,
        "title": page.title,
        "content": page.content,
        "domain": page.domain,
        "success": page.success,
        "error": page.error,
    }


def serialize_retrieved_context(item) -> dict:
    return {
        "node_id": item.node_id,
        "content": item.content,
        "url": item.url,
        "title": item.title,
        "domain": item.domain,
        "score": item.score,
        "hop_depth": item.hop_depth,
    }


def serialize_ranked_chunk(chunk) -> dict:
    return {
        "content": chunk.content,
        "url": chunk.url,
        "title": chunk.title,
        "domain": chunk.domain,
        "score": chunk.score,
        "relevance": chunk.relevance,
        "reason": chunk.reason,
    }


def serialize_reasoning(reasoning) -> dict | None:
    if not reasoning:
        return None
    return {
        "steps": [
            {
                "step_number": step.step_number,
                "agent": step.agent,
                "action": step.action,
                "detail": step.detail,
                "confidence": step.confidence,
            }
            for step in reasoning.steps
        ],
        "key_findings": reasoning.key_findings,
        "confidence": reasoning.confidence,
        "reasoning_summary": reasoning.reasoning_summary,
    }


def serialize_final_answer(answer) -> dict | None:
    if not answer:
        return None
    return {
        "answer": answer.answer,
        "summary": answer.summary,
        "confidence": answer.confidence,
        "citations": [
            {
                "number": citation.number,
                "url": citation.url,
                "title": citation.title,
                "domain": citation.domain,
            }
            for citation in answer.citations
        ],
    }


def build_sources_table(search_results: list, scraped_pages: list, ranked_chunks: list) -> list[dict]:
    scraped_urls = {page.url for page in scraped_pages if getattr(page, "success", False)}
    chunk_map: dict[str, str] = {}
    for chunk in ranked_chunks:
        chunk_map.setdefault(chunk.url, chunk.content[:250])

    table = []
    for src in search_results:
        table.append(
            {
                "title": src.title,
                "url": src.url,
                "domain": src.domain,
                "snippet": chunk_map.get(src.url, src.snippet or ""),
                "scraped": src.url in scraped_urls,
                "source": src.source,
            }
        )
    return table


def serialize_graph(graph_state) -> dict:
    if not graph_state or graph_state.graph.number_of_nodes() == 0:
        return {
            "nodes": [],
            "edges": [],
            "html": "",
            "stats": {"nodes": 0, "edges": 0, "top_domains": []},
        }

    graph = graph_state.graph
    nodes = []
    for node_id, data in graph.nodes(data=True):
        nodes.append(
            {
                "id": node_id,
                "title": data.get("title", ""),
                "url": data.get("url", ""),
                "domain": data.get("domain", ""),
                "content": data.get("content", ""),
                "chunk_index": data.get("chunk_index", 0),
                "doc_index": data.get("doc_index", 0),
            }
        )

    edges = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "type": data.get("type", ""),
                "weight": data.get("weight", 0),
            }
        )

    from utils.graph_viz import graph_to_html

    domains = [data.get("domain", "") for _, data in graph.nodes(data=True)]
    top_domains = [
        {"domain": domain or "unknown", "count": count}
        for domain, count in Counter(domains).most_common(10)
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "html": graph_to_html(graph, height="560px"),
        "stats": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "top_domains": top_domains,
        },
    }


def serialize_result(result, followups: list[str]) -> dict:
    timings = result.timings or {}
    search_results = result.search_results or []
    scraped_pages = result.scraped_pages or []
    ranked_chunks = result.ranked_chunks or []
    final_answer = serialize_final_answer(result.final_answer)
    reasoning = serialize_reasoning(result.reasoning)
    sources_table = build_sources_table(search_results, scraped_pages, ranked_chunks)
    successful_pages = sum(1 for page in scraped_pages if page.success)

    return {
        "query": result.query,
        "success": result.success,
        "error": result.error,
        "query_plan": serialize_query_plan(result.query_plan),
        "search_results": [serialize_search_result(item) for item in search_results],
        "scraped_pages": [serialize_scraped_page(item) for item in scraped_pages],
        "retrieved": [serialize_retrieved_context(item) for item in result.retrieved],
        "ranked_chunks": [serialize_ranked_chunk(item) for item in ranked_chunks],
        "reasoning": reasoning,
        "final_answer": final_answer,
        "step_log": result.step_log,
        "timings": timings,
        "followups": followups,
        "sources_table": sources_table,
        "graph": serialize_graph(result.graph_state),
        "stats": {
            "total_time_seconds": round(sum(timings.values()), 2),
            "source_count": len(search_results),
            "successful_scrapes": successful_pages,
            "confidence_percent": int((final_answer or {}).get("confidence", 0) * 100),
            "display_source_count": successful_pages or len(search_results),
        },
    }
