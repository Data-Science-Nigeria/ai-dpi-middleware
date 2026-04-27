from spitch import Spitch

_client: Spitch | None = None

def get_client(api_key: str) -> Spitch:
    global _client
    if _client is None:
        _client = Spitch(api_key=api_key)
    return _client
