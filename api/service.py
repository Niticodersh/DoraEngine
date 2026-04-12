"""Shared business logic used by HTTP handlers and the React-facing API."""
from __future__ import annotations

import os
import re

from api.constants import AGENT_STAGES
from api.serializers import serialize_result
from pipeline.orchestrator import run_research


def clean_text(text: str) -> str:
    text = re.sub(r"(\b\w\b\s+){2,}", lambda match: match.group(0).replace(" ", ""), text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("**", "")
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    return text.strip()


def require_query(query: str) -> str:
    normalized = (query or "").strip()
    if not normalized:
        raise ValueError("Query is required")
    return normalized


def ensure_api_key() -> None:
    if os.getenv("GROQ_API_KEY"):
        return

    try:
        import streamlit as st

        if st.secrets.get("GROQ_API_KEY"):
            return
    except Exception:
        pass

    raise RuntimeError("GROQ_API_KEY not set")


def generate_followup_questions(query: str, answer: str, n: int = 6) -> list[str]:
    if not answer:
        return []

    try:
        from utils.llm_client import LLMClient

        llm = LLMClient()
        prompt = f"""Based on this question: '{query}' and this answer: '{answer}', generate {n} contextual follow-up questions that would help explore the topic further.

Make them specific, insightful, and varied. Focus on:
- Deeper understanding of key concepts
- Practical applications
- Related topics or comparisons
- Potential limitations or risks
- Future developments

Return only the questions, one per line, numbered 1. 2. etc."""

        response = llm.chat([{"role": "user", "content": prompt}])
        questions = []
        for line in response.splitlines():
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit():
                line = re.sub(r"^\d+\.\s*", "", line)
            elif line.startswith("-"):
                line = line[1:].strip()
            else:
                continue
            if line:
                questions.append(clean_text(line))

        if len(questions) >= n:
            return questions[:n]
    except Exception:
        pass

    fallback = [
        f"What is the next most important question about {query}?",
        "How can I apply this answer in practice?",
        "What risks should I watch for with this topic?",
        "What related topic should I explore next?",
        "What are the common myths about this subject?",
        "How might this area change over the next few years?",
    ]
    return fallback[:n]


def stage_payload(agent: str) -> dict | None:
    for stage in AGENT_STAGES:
        if stage["agent"] == agent:
            return stage
    return None


def run_research_payload(query: str, progress_callback=None) -> dict:
    normalized_query = require_query(query)
    ensure_api_key()

    result = run_research(normalized_query, progress_callback=progress_callback)
    followups = []
    if result.success and result.final_answer:
        followups = generate_followup_questions(normalized_query, result.final_answer.answer)
    return serialize_result(result, followups)
