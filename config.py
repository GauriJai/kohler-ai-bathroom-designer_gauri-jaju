"""
Environment/config loading. Never hardcode API keys -- everything comes
from environment variables, loaded from a local .env file if present
(see .env.example for the template).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist; safe to call multiple times


def openai_key_status() -> str:
    """
    Returns "configured" or "missing" WITHOUT ever exposing the key value
    itself -- the UI uses this to show an honest mock-mode banner.
    """
    key = os.environ.get("OPENAI_API_KEY", "")
    return "configured" if key.strip() else "missing"
