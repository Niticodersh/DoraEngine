"""Shared API-facing constants for frontend and backend."""

SUGGESTIONS = [
    "Latest advances in AI agents",
    "Explain quantum computing simply",
    "Best open-source LLMs in 2025",
    "How AlphaFold works",
    "Future of self-driving cars",
    "Graph RAG vs vector RAG",
]

AGENT_STAGES = [
    {"agent": "QueryAgent", "label": "Understanding your question...", "progress": 0.08},
    {"agent": "SearchAgent", "label": "Searching the web for sources...", "progress": 0.20},
    {"agent": "ScraperAgent", "label": "Reading the most relevant pages...", "progress": 0.42},
    {"agent": "GraphBuilder", "label": "Organizing what we found...", "progress": 0.60},
    {"agent": "GraphRAG", "label": "Connecting related information...", "progress": 0.72},
    {"agent": "RankingAgent", "label": "Picking the most useful details...", "progress": 0.82},
    {"agent": "ReasoningAgent", "label": "Thinking it through...", "progress": 0.90},
    {"agent": "AnswerAgent", "label": "Writing your answer...", "progress": 0.97},
]
