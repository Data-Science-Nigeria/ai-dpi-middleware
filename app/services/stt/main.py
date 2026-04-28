from app.services.stt.providers import groq as groq_provider
from app.services.stt.providers import openai as openai_provider
from app.services.stt.providers import spitch as spitch_provider


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    provider: str,
    model: str,
    language: str | None = None,
    prompt: str | None = None,
    special_words: str | None = None,
    timestamp: str = "none",
) -> dict:
    if provider == "groq":
        return await groq_provider.transcribe(
            file_bytes=file_bytes, filename=filename, content_type=content_type,
            model=model, language=language, prompt=prompt,
        )
    if provider == "openai":
        return await openai_provider.transcribe(
            file_bytes=file_bytes, filename=filename, content_type=content_type,
            model=model, language=language, prompt=prompt,
        )
    if provider == "spitch":
        return await spitch_provider.transcribe(
            file_bytes=file_bytes, filename=filename, content_type=content_type,
            model=model, language=language or "en",
            special_words=special_words, timestamp=timestamp,
        )
    raise ValueError(f"Unsupported provider: {provider!r}")
