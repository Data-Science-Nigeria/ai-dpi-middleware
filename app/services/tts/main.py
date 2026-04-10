from app.services.tts.providers import groq as groq_provider
from app.services.tts.providers import openai as openai_provider


async def synthesize(
    text: str,
    voice: str | None,
    model: str,
    response_format: str,
    provider: str,
    speed: float = 1.0,
    instructions: str | None = None,
    language = None
) -> bytes:
    if provider == "groq":
        return await groq_provider.synthesize(
            text=text, voice=voice, model=model, response_format=response_format
        )
    if provider == "openai":
        return await openai_provider.synthesize(
            text=text, voice=voice, model=model, response_format=response_format,
            speed=speed, instructions=instructions,
        )
    raise ValueError(f"Unsupported provider: {provider!r}")
