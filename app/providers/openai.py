from openai import OpenAI

_client: OpenAI | None = None


def get_client(api_key: str) -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client
