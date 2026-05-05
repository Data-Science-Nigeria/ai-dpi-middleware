from app.services.chat.providers import generic

async def chat(
    messages: list[dict],
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
    **kwargs,
) -> str:
    return await generic.chat(
        messages=messages,
        model=model,
        system=system,
        provider="openai",
        url="https://api.openai.com/v1/responses",
        max_tokens=max_tokens,
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
        provider="openai",
        url="https://api.openai.com/v1/responses",
        max_tokens=max_tokens,
        **kwargs,
    )
