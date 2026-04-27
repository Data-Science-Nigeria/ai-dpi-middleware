import anthropic

_client: anthropic.AsyncAnthropic | None = None


def get_client(api_key: str) -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client