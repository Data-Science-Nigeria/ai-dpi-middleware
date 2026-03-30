from app.services.tts.providers import groq as groq_provider


async def synthesize(
    text: str,
    voice: str | None,
    model: str,
    response_format: str,
    provider: str,
) -> bytes:
    if provider == "groq":
        return await groq_provider.synthesize(
            text=text, voice=voice, model=model, response_format=response_format
        )
    raise ValueError(f"Unsupported provider: {provider!r}")
