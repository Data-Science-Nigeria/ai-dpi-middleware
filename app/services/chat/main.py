import yaml

from app.config import get_config
from app.services.chat.providers import anthropic as anthropic_provider
from app.services.chat.providers import gemini as gemini_provider
from app.services.chat.providers import groq as groq_provider
from app.services.chat.providers import openai as openai_provider


async def chat(
    messages: list[dict],
    provider: str,
    model: str,
    context: str | None = None,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    if system is None:
        cfg = get_config()
        has_system = cfg['llm'].get("system_prompt_path", None)
        if has_system:
            with open(cfg['llm']['system_prompt_path']) as f:
                raw = yaml.safe_load(f) or {}
                system = raw.get('SYSTEM_PROMPT', None)
                if not isinstance(system, str):
                    system = None

    if system is not None and system.find("{context}"):
        system = system.format(document=context)

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
            documents=[context] if context else None,
        )
    if provider == "gemini":
        return await gemini_provider.chat(
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
    elif provider == "gemini":
        async for chunk in gemini_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        ):
            yield chunk
    else:
        raise ValueError(f"Unsupported provider: {provider!r}")
