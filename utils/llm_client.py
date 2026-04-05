"""
LLM Client — Groq wrapper using openai/gpt-oss-120b
"""
from __future__ import annotations

import os
from typing import Optional
from dotenv import load_dotenv
from groq import Groq, AsyncGroq

load_dotenv()

import streamlit as st

_GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

_MODEL = "openai/gpt-oss-120b"


class LLMClient:
    """Thin synchronous + async wrapper around the Groq client."""

    def __init__(self, api_key: Optional[str] = None, model: str = _MODEL):
        key = api_key or _GROQ_API_KEY
        if not key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        self.model = model
        self._client = Groq(api_key=key)
        self._async_client = AsyncGroq(api_key=key)

    # ------------------------------------------------------------------
    # Synchronous
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system: Optional[str] = None,
    ) -> str:
        """Run a synchronous chat completion and return the response text."""
        if system:
            messages = [{"role": "system", "content": system}] + messages
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def complete(self, prompt: str, **kwargs) -> str:
        """Simple single-turn prompt → response helper."""
        return self.chat(
            messages=[{"role": "user", "content": prompt}], **kwargs
        )

    # ------------------------------------------------------------------
    # Asynchronous
    # ------------------------------------------------------------------
    async def achat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system: Optional[str] = None,
    ) -> str:
        """Run an async chat completion and return the response text."""
        if system:
            messages = [{"role": "system", "content": system}] + messages
        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def acomplete(self, prompt: str, **kwargs) -> str:
        """Simple async single-turn prompt → response helper."""
        return await self.achat(
            messages=[{"role": "user", "content": prompt}], **kwargs
        )


# Module-level singleton — import and use directly
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
