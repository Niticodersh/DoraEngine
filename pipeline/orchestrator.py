"""
LangGraph Pipeline Orchestrator — wires all 9 agents into a StateGraph.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# TypedDict from typing (Python 3.8+)
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

# LangGraph 0.2.x API
from langgraph.graph import StateGraph, END

# Agents
from agents.query_agent    import run_query_agent, QueryPlan
from agents.search_agent   import run_search_agent, SearchResult

_progress_callback: Optional[Callable[[str, str], None]] = None
from agents.scraper_agent  import run_scraper_agent, ScrapedPage
from agents.graph_builder  import build_graph, GraphState
from agents.graph_rag      import retrieve, RetrievedContext
from agents.ranking_agent  import run_ranking_agent, RankedChunk
from agents.reasoning_agent import run_reasoning_agent, ReasoningTrace
from agents.answer_agent   import run_answer_agent, FinalAnswer


# ──────────────────────────────────────────────────────────────────────
# Shared pipeline state (TypedDict for LangGraph)
# ──────────────────────────────────────────────────────────────────────
class PipelineState(TypedDict, total=False):
    # Input
    query: str

    # Agent outputs
    query_plan:      QueryPlan
    search_results:  list[SearchResult]
    scraped_pages:   list[ScrapedPage]
    graph_state:     GraphState
    retrieved:       list[RetrievedContext]
    ranked_chunks:   list[RankedChunk]
    reasoning:       ReasoningTrace
    final_answer:    FinalAnswer

    # Progress tracking
    step_log:        list[dict]
    error:           Optional[str]
    timings:         dict[str, float]


# ──────────────────────────────────────────────────────────────────────
# Result object returned to the UI
# ──────────────────────────────────────────────────────────────────────
@dataclass
class ResearchResult:
    query:           str
    query_plan:      Optional[QueryPlan]
    search_results:  list[SearchResult]
    scraped_pages:   list[ScrapedPage]
    graph_state:     Optional[GraphState]
    retrieved:       list[RetrievedContext]
    ranked_chunks:   list[RankedChunk]
    reasoning:       Optional[ReasoningTrace]
    final_answer:    Optional[FinalAnswer]
    step_log:        list[dict]
    timings:         dict[str, float]
    success:         bool
    error:           Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# Helper: step logger
# ──────────────────────────────────────────────────────────────────────
def _log(state: PipelineState, agent: str, action: str, detail: str = "") -> None:
    state.setdefault("step_log", [])
    state.setdefault("timings", {})
    state["step_log"].append(
        {
            "agent":  agent,
            "action": action,
            "detail": detail,
            "ts":     time.time(),
        }
    )
    if _progress_callback is not None:
        _progress_callback(agent, action)


def _time_it(state: PipelineState, key: str) -> float:
    state.setdefault("timings", {})
    t = time.time()
    state["timings"][key] = t
    return t


# ──────────────────────────────────────────────────────────────────────
# Node functions (one per agent)
# ──────────────────────────────────────────────────────────────────────
def node_query(state: PipelineState) -> PipelineState:
    t0 = time.time()
    query = state["query"]
    _log(state, "QueryAgent", "Expanding query", f"Original: {query}")

    plan = run_query_agent(query)
    state["query_plan"] = plan
    state["timings"]["query_agent"] = time.time() - t0

    _log(state, "QueryAgent", "Query expanded",
         f"Sub-queries: {len(plan.sub_queries)} | Intent: {plan.intent}")
    return state


def node_search(state: PipelineState) -> PipelineState:
    t0   = time.time()
    plan = state["query_plan"]
    _log(state, "SearchAgent", "Searching web", f"Running {len(plan.search_queries)} queries")

    results = run_search_agent(plan.search_queries)
    state["search_results"] = results
    state["timings"]["search_agent"] = time.time() - t0

    _log(state, "SearchAgent", "Search complete",
         f"Found {len(results)} unique URLs")
    return state


def node_scrape(state: PipelineState) -> PipelineState:
    t0      = time.time()
    results = state.get("search_results", [])
    urls    = [r.url for r in results][:25]  # Limit to 25 URLs to scrape
    _log(state, "ScraperAgent", "Scraping sources",
         f"Scraping {len(urls)} URLs in parallel")

    pages = run_scraper_agent(urls)
    state["scraped_pages"] = pages
    state["timings"]["scraper_agent"] = time.time() - t0

    ok = sum(1 for p in pages if p.success)
    _log(state, "ScraperAgent", "Scraping complete",
         f"{ok}/{len(urls)} pages scraped successfully")
    return state


def node_build_graph(state: PipelineState) -> PipelineState:
    t0    = time.time()
    pages = state.get("scraped_pages", [])
    _log(state, "GraphBuilder", "Building knowledge graph",
         f"Processing {len(pages)} scraped pages")

    gs = build_graph(pages)
    state["graph_state"] = gs
    state["timings"]["graph_builder"] = time.time() - t0

    _log(state, "GraphBuilder", "Graph built",
         f"{gs.graph.number_of_nodes()} nodes, {gs.graph.number_of_edges()} edges")
    return state


def node_retrieve(state: PipelineState) -> PipelineState:
    t0    = time.time()
    gs    = state["graph_state"]
    query = state["query_plan"].refined_query
    _log(state, "GraphRAG", "Retrieving context",
         f"Multi-hop retrieval from {gs.graph.number_of_nodes()} nodes")

    retrieved = retrieve(query, gs)
    state["retrieved"] = retrieved
    state["timings"]["graph_rag"] = time.time() - t0

    _log(state, "GraphRAG", "Retrieval complete",
         f"Retrieved {len(retrieved)} context chunks across up to 2 hops")
    return state


def node_rank(state: PipelineState) -> PipelineState:
    t0        = time.time()
    retrieved = state.get("retrieved", [])
    query     = state["query"]
    _log(state, "RankingAgent", "Re-ranking chunks",
         f"Scoring {len(retrieved)} candidates with LLM")

    ranked = run_ranking_agent(query, retrieved)
    state["ranked_chunks"] = ranked
    state["timings"]["ranking_agent"] = time.time() - t0

    _log(state, "RankingAgent", "Ranking complete",
         f"Top {len(ranked)} chunks selected")
    return state


def node_reason(state: PipelineState) -> PipelineState:
    t0     = time.time()
    chunks = state.get("ranked_chunks", [])
    query  = state["query"]
    _log(state, "ReasoningAgent", "Performing multi-step reasoning",
         f"Reasoning over {len(chunks)} ranked chunks")

    reasoning = run_reasoning_agent(query, chunks)
    state["reasoning"] = reasoning
    state["timings"]["reasoning_agent"] = time.time() - t0

    _log(state, "ReasoningAgent", "Reasoning complete",
         f"{len(reasoning.steps)} reasoning steps | Confidence: {reasoning.confidence:.0%}")
    return state


def node_answer(state: PipelineState) -> PipelineState:
    t0        = time.time()
    chunks    = state.get("ranked_chunks", [])
    reasoning = state["reasoning"]
    query     = state["query"]
    _log(state, "AnswerAgent", "Generating final answer",
         "Synthesising from context + reasoning trace")

    answer = run_answer_agent(query, chunks, reasoning)
    state["final_answer"] = answer
    state["timings"]["answer_agent"] = time.time() - t0

    _log(state, "AnswerAgent", "Answer ready",
         f"Confidence: {answer.confidence:.0%} | Citations: {len(answer.citations)}")
    return state


# ──────────────────────────────────────────────────────────────────────
# Build the LangGraph
# ──────────────────────────────────────────────────────────────────────
def _build_pipeline() -> Any:
    g = StateGraph(PipelineState)

    g.add_node("process_query",       node_query)
    g.add_node("search",      node_search)
    g.add_node("scrape",      node_scrape)
    g.add_node("build_graph", node_build_graph)
    g.add_node("retrieve",    node_retrieve)
    g.add_node("rank",        node_rank)
    g.add_node("reason",      node_reason)
    g.add_node("answer",      node_answer)

    g.set_entry_point("process_query")
    g.add_edge("process_query",       "search")
    g.add_edge("search",      "scrape")
    g.add_edge("scrape",      "build_graph")
    g.add_edge("build_graph", "retrieve")
    g.add_edge("retrieve",    "rank")
    g.add_edge("rank",        "reason")
    g.add_edge("reason",      "answer")
    g.add_edge("answer",      END)

    return g.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = _build_pipeline()
    return _pipeline


# ──────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────
def run_research(
    query: str,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> ResearchResult:
    """
    Run the full research pipeline.

    Args:
        query:             The user's research query.
        progress_callback: Optional fn(agent_name, action) called after each step.

    Returns:
        ResearchResult with all intermediate + final outputs.
    """
    pipeline = get_pipeline()

    initial_state: PipelineState = {
        "query":    query,
        "step_log": [],
        "timings":  {},
    }

    global _progress_callback
    _progress_callback = progress_callback

    try:
        final_state: PipelineState = pipeline.invoke(initial_state)
        return ResearchResult(
            query          = query,
            query_plan     = final_state.get("query_plan"),
            search_results = final_state.get("search_results", []),
            scraped_pages  = final_state.get("scraped_pages", []),
            graph_state    = final_state.get("graph_state"),
            retrieved      = final_state.get("retrieved", []),
            ranked_chunks  = final_state.get("ranked_chunks", []),
            reasoning      = final_state.get("reasoning"),
            final_answer   = final_state.get("final_answer"),
            step_log       = final_state.get("step_log", []),
            timings        = final_state.get("timings", {}),
            success        = True,
        )
    except Exception as e:
        import traceback
        return ResearchResult(
            query          = query,
            query_plan     = None,
            search_results = [],
            scraped_pages  = [],
            graph_state    = None,
            retrieved      = [],
            ranked_chunks  = [],
            reasoning      = None,
            final_answer   = None,
            step_log       = [],
            timings        = {},
            success        = False,
            error          = f"{e}\n\n{traceback.format_exc()}",
        )
    finally:
        _progress_callback = None
