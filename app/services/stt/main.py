from app.services.stt.providers import groq as groq_provider
from app.services.stt.providers import openai as openai_provider


async def transcribe(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    provider: str,
    model: str,
    language: str | None = None,
    prompt: str | None = None,
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
    raise ValueError(f"Unsupported provider: {provider!r}")
