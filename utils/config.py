"""Configuration helpers shared across Streamlit and API entry points."""
from __future__ import annotations

import os

# Load .env file into environment variables at import time.
# This ensures MONGODB_URI, AUTH_SECRET_KEY, etc. are available when running
# the backend with uvicorn (which does not auto-load .env files).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — rely on environment variables being set externally


def get_secret(name: str, default: str = "") -> str:
    env_value = os.getenv(name, "")
    if env_value:
        return env_value

    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass

    return default
