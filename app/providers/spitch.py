from spitch import Spitch

from app.config import settings

_client: Spitch | None = None


def get_client() -> Spitch:
    global _client
    if _client is None:
        _client = Spitch(api_key=settings.spitch_api_key)
    return _client
