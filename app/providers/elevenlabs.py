from __future__ import annotations

from elevenlabs.client import ElevenLabs

from app.config import get_config

_client: ElevenLabs | None = None


def get_client() -> ElevenLabs:
    global _client
    if _client is None:
        api_key = get_config().get("speech", {}).get("providers", {}).get("elevenlabs", {}).get("api_key", "")
        _client = ElevenLabs(api_key=api_key)
    return _client
