"""
Answer Agent — synthesises the final answer from reasoning + context.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from utils.llm_client import get_llm_client
from agents.ranking_agent import RankedChunk
from agents.reasoning_agent import ReasoningTrace


@dataclass
class Citation:
    number: int
    url:    str
    title:  str
    domain: str


@dataclass
class FinalAnswer:
    answer:     str
    citations:  list[Citation]
    confidence: float
    summary:    str           # one-sentence TL;DR


_SYSTEM = """You are a senior academic researcher and expert synthesiser. Your job is to write a formally structured, highly professional research document to answer the user's research query.

Instructions:
- Write in well-structured markdown.
- Adopt a formal, academic tone. Do NOT use conversational language.
- Structure your response with the following headers:
  - '## Abstract' (A clear, concise summary of your findings — 3 to 4 sentences).
  - '## Introduction' (Introduce the topic and its significance).
  - '## Technical Analysis' or '## Key Findings' (Detailed, fact-based breakdown).
  - '## Conclusion'
- Be specific: cite facts from the provided context.
- Use numbered citations [1], [2] etc. where appropriate in the text.
- Do NOT fabricate information not present in the context.
- Be concise but thorough — aim for 600-1000 words.
"""


def run_answer_agent(
    query: str,
    ranked_chunks: list[RankedChunk],
    reasoning: ReasoningTrace,
) -> FinalAnswer:
    """
    Generate the final research answer with citations.
    """
    if not ranked_chunks:
        return FinalAnswer(
            answer     = "I was unable to find sufficient information to answer this query.",
            citations  = [],
            confidence = 0.0,
            summary    = "No results found.",
        )

    # Build numbered context for citations
    sources: list[RankedChunk] = []
    seen_urls: set[str] = set()
    for chunk in ranked_chunks:
        if chunk.url not in seen_urls:
            seen_urls.add(chunk.url)
            sources.append(chunk)

    context_block = "\n\n".join(
        f"[{i+1}] (Source: {s.domain} — {s.url})\n{s.content[:700]}"
        for i, s in enumerate(sources[:10])
    )

    reasoning_summary = (
        f"Reasoning summary: {reasoning.reasoning_summary}\n"
        f"Key findings:\n" + "\n".join(f"  • {f}" for f in reasoning.key_findings)
        if reasoning.reasoning_summary else ""
    )

    prompt = (
        f"Research Query: {query}\n\n"
        f"{reasoning_summary}\n\n"
        f"Context (numbered for citations):\n{context_block}\n\n"
        f"Write a comprehensive, well-cited markdown answer."
    )

    llm = get_llm_client()

    try:
        answer_text = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=_SYSTEM,
            temperature=0.4,
            max_tokens=3000,
        )
    except Exception as e:
        print(f"[AnswerAgent] Error: {e}")
        answer_text = (
            "## Answer\n\n"
            + "\n\n".join(c.content[:300] for c in ranked_chunks[:3])
        )

    # Build citation list from sources actually present
    citations = [
        Citation(
            number = i + 1,
            url    = s.url,
            title  = s.title or s.domain,
            domain = s.domain,
        )
        for i, s in enumerate(sources[:10])
    ]

    # Extract Abstract if present
    summary = ""
    if "## Abstract" in answer_text:
        try:
            abstract_block = answer_text.split("## Abstract")[1].split("##")[0].strip()
            summary    = abstract_block[:400].strip("*_ \n")
        except Exception:
            summary = query

    if not summary:
        summary = ranked_chunks[0].content[:200] if ranked_chunks else query

    return FinalAnswer(
        answer     = answer_text,
        citations  = citations,
        confidence = reasoning.confidence,
        summary    = summary,
    )
