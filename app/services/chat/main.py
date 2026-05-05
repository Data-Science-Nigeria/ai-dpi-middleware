from app.services.chat.providers import anthropic as anthropic_provider
from app.services.chat.providers import groq as groq_provider
from app.services.chat.providers import openai as openai_provider


async def chat(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    if provider == "anthropic":
        return await anthropic_provider.chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "openai":
        return await openai_provider.chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "groq":
        return await groq_provider.chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    raise ValueError(f"Unsupported provider: {provider!r}")


async def stream_chat(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None = None,
    max_tokens: int = 1024,
):
    if provider == "anthropic":
        async for chunk in anthropic_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        ):
            yield chunk
    elif provider == "openai":
        async_iter = await openai_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
        async for chunk in async_iter:
            yield chunk
    elif provider == "groq":
        async_iter = await groq_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
        async for chunk in async_iter:
            yield chunk
    else:
        raise ValueError(f"Unsupported provider: {provider!r}")
