from __future__ import annotations

from deepgram import DeepgramClient

from app.config import get_config

_client: DeepgramClient | None = None


def get_client() -> DeepgramClient:
    global _client
    if _client is None:
        api_key = get_config().get("speech", {}).get("providers", {}).get("deepgram", {}).get("api_key", "")
        _client = DeepgramClient(api_key)
    return _client
