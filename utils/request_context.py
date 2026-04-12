"""Per-request runtime configuration for the agent pipeline."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar


_groq_api_key: ContextVar[str | None] = ContextVar("groq_api_key", default=None)
_tavily_api_key: ContextVar[str | None] = ContextVar("tavily_api_key", default=None)


def get_groq_api_key() -> str | None:
    return _groq_api_key.get()


def get_tavily_api_key() -> str | None:
    return _tavily_api_key.get()


@contextmanager
def request_config(groq_api_key: str | None = None, tavily_api_key: str | None = None):
    groq_token = _groq_api_key.set(groq_api_key)
    tavily_token = _tavily_api_key.set(tavily_api_key)
    try:
        yield
    finally:
        _groq_api_key.reset(groq_token)
        _tavily_api_key.reset(tavily_token)
