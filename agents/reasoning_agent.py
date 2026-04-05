"""
Reasoning Agent — multi-step chain-of-thought reasoning over ranked context.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from utils.llm_client import get_llm_client
from agents.ranking_agent import RankedChunk


@dataclass
class ReasoningStep:
    step_number: int
    agent:       str
    action:      str
    detail:      str
    confidence:  float


@dataclass
class ReasoningTrace:
    steps:           list[ReasoningStep]
    key_findings:    list[str]
    confidence:      float
    reasoning_summary: str


_SYSTEM = """You are an expert multi-step research analyst. Given a query and supporting context chunks,
perform thorough chain-of-thought reasoning.

You MUST respond with valid JSON matching this exact schema:
{
  "steps": [
    {
      "step_number": 1,
      "action": "Brief action title",
      "detail": "Detailed explanation of what you found or reasoned",
      "confidence": 0.85
    }
  ],
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "overall_confidence": 0.82,
  "reasoning_summary": "One paragraph summarising the reasoning chain"
}

Guidelines:
- Use 4-7 reasoning steps
- Each step should build on previous ones
- Cite specific information from the context
- Be honest about uncertainty
- overall_confidence should reflect evidence strength (0.0-1.0)"""


def run_reasoning_agent(
    query: str,
    ranked_chunks: list[RankedChunk],
) -> ReasoningTrace:
    """
    Perform structured chain-of-thought reasoning over retrieved context.
    """
    if not ranked_chunks:
        return ReasoningTrace(
            steps=[],
            key_findings=["No relevant context found."],
            confidence=0.0,
            reasoning_summary="No context available for reasoning.",
        )

    # Build context block (top 8 most relevant)
    context_block = "\n\n---\n\n".join(
        f"[Source: {c.domain}]\n{c.content[:600]}"
        for c in ranked_chunks[:8]
    )
    prompt = (
        f"Research Query: {query}\n\n"
        f"Context:\n{context_block}\n\n"
        f"Perform step-by-step reasoning to answer the query."
    )

    llm = get_llm_client()
    steps: list[ReasoningStep] = []

    try:
        raw = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=_SYSTEM,
            temperature=0.3,
            max_tokens=2048,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)

        for s in data.get("steps", []):
            steps.append(
                ReasoningStep(
                    step_number = s.get("step_number", len(steps) + 1),
                    agent       = "ReasoningAgent",
                    action      = s.get("action", ""),
                    detail      = s.get("detail", ""),
                    confidence  = float(s.get("confidence", 0.5)),
                )
            )

        return ReasoningTrace(
            steps              = steps,
            key_findings       = data.get("key_findings", []),
            confidence         = float(data.get("overall_confidence", 0.5)),
            reasoning_summary  = data.get("reasoning_summary", ""),
        )

    except Exception as e:
        print(f"[ReasoningAgent] Error: {e}")
        # Fallback: minimal trace
        return ReasoningTrace(
            steps=[
                ReasoningStep(
                    step_number = 1,
                    agent       = "ReasoningAgent",
                    action      = "Context review",
                    detail      = f"Reviewed {len(ranked_chunks)} context chunks.",
                    confidence  = 0.5,
                )
            ],
            key_findings    = [c.content[:150] for c in ranked_chunks[:3]],
            confidence      = 0.5,
            reasoning_summary = "Reasoning encountered an error; using raw context.",
        )
