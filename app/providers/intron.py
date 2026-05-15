from __future__ import annotations

from app.config import get_config

# Intron has no official Python SDK — all calls go through httpx.
# This module centralises config access so service providers don't import get_config directly.

def get_api_key() -> str:
    return get_config().get("speech", {}).get("providers", {}).get("intron", {}).get("api_key", "")


def get_base_url() -> str:
    return (
        get_config()
        .get("speech", {})
        .get("providers", {})
        .get("intron", {})
        .get("base_url", "https://api.intron.africa/v1")
    )
