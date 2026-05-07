from app.config import get_config
from app.services.embedding.providers import openai as openai_provider


async def get_embedding(
    text: str,
    model: str | None = None,
):
    cfg = get_config()["llm"]["embedding_model"]
    model = model or cfg['model']
    if cfg['provider'] == "openai":
        return await openai_provider.get_embedding(
            text=text,
            model=model
        )
    raise ValueError(f"Unsupported provider: {cfg['provider']!r}")

