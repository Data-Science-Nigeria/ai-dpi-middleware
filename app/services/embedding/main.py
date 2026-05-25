from app.config import get_config
from app.services.embedding.providers import local as local_provider
from app.services.embedding.providers import openai as openai_provider

_PROVIDERS = {
    "openai": openai_provider,
    "local": local_provider,
}


async def get_embedding(
    text: str,
    model: str | None = None,
) -> list[float]:
    cfg = get_config()["llm"]["embedding_model"]
    model = model or cfg["model"]
    provider_name = cfg.get("provider", "openai")
    provider = _PROVIDERS.get(provider_name)
    if provider is None:
        raise ValueError(
            f"Unsupported embedding provider: {provider_name!r}. "
            f"Supported: {sorted(_PROVIDERS)}."
        )
    return await provider.get_embedding(text=text, model=model)

