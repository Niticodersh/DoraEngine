"""Configuration helpers shared across Streamlit and API entry points."""
from __future__ import annotations

import os


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
