import yaml

from app.config import get_config
from app.services.chat.providers import anthropic as anthropic_provider
from app.services.chat.providers import gemini as gemini_provider
from app.services.chat.providers import groq as groq_provider
from app.services.chat.providers import ollama as ollama_provider
from app.services.chat.providers import openai as openai_provider


def _load_system_prompt(cfg: dict) -> str | None:
    import os
    path = cfg["llm"].get("system_prompt_path")
    if not path or not os.path.isfile(path):
        return None
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
        prompt = raw.get("SYSTEM_PROMPT")
        return prompt if isinstance(prompt, str) else None


async def chat(
    messages: list[dict],
    provider: str,
    model: str,
    context: str | None = None,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    cfg = get_config()

    if system is None:
        system = _load_system_prompt(cfg)

    if system is not None and "{context}" in system:
        system = system.format(context=context or "")

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
    if provider == "ollama":
        return await ollama_provider.chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )

    raise ValueError(f"Unsupported provider: {provider!r}")


async def _resolve_stream(
    messages: list[dict],
    provider: str,
    model: str,
    system: str | None,
    max_tokens: int,
):
    if provider == "anthropic":
        return anthropic_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "openai":
        return await openai_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "groq":
        return await groq_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "gemini":
        return gemini_provider.stream_chat(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
        )
    if provider == "ollama":
        return ollama_provider.stream_chat(
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
    cfg = get_config()

    if system is None:
        system = _load_system_prompt(cfg)

    async_iter = await _resolve_stream(
        messages=messages, provider=provider, model=model,
        system=system, max_tokens=max_tokens,
    )
    async for chunk in async_iter:
        yield chunk
