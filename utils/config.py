"""Configuration helpers for the API server.

Environment variables take priority. Falls back to `default` if the var is not set.
Streamlit's secrets API is no longer used — the API server is a standalone FastAPI
process where env vars are the only secret source.
"""
from __future__ import annotations

import os

# Load .env file into environment variables at import time.
# On Render / production env vars are injected directly; .env is ignored.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — rely on env vars set externally


def get_secret(name: str, default: str = "") -> str:
    """Return the value of *name* from the environment, or *default*."""
    return os.getenv(name, default)
