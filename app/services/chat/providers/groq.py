from app.services.chat.providers import generic

async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    documents: list[str] | None = None,
    **kwargs,
) -> str:
    return await generic.chat(
        messages=messages,
        model=model,
        system=system,
        provider="groq",
        url="https://api.groq.com/openai/v1/chat/completions",
        max_tokens=max_tokens,
        documents=documents,
        **kwargs,
    )


async def stream_chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
):
    return generic.stream_chat(
        messages=messages,
        model=model,
        system=system,
        provider="groq",
        url="https://api.groq.com/openai/v1/chat/completions",
        max_tokens=max_tokens,
        **kwargs,
    )
