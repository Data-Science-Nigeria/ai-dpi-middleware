from groq import Groq

_client: Groq | None = None


def get_client(api_key: str) -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=api_key)
    return _client