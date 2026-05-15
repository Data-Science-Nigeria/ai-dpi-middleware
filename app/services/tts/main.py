from app.services.tts.providers import elevenlabs as elevenlabs_provider
from app.services.tts.providers import groq as groq_provider
from app.services.tts.providers import intron as intron_provider
from app.services.tts.providers import openai as openai_provider
from app.services.tts.providers import spitch as spitch_provider


async def synthesize(
    text: str,
    voice: str | None,
    model: str,
    response_format: str,
    provider: str,
    speed: float = 1.0,
    instructions: str | None = None,
    language: str | None = None,
) -> bytes:
    if provider == "groq":
        return await groq_provider.synthesize(
            text=text, voice=voice, model=model, response_format=response_format,
        )
    if provider == "openai":
        return await openai_provider.synthesize(
            text=text, voice=voice, model=model, response_format=response_format,
            speed=speed, instructions=instructions,
        )
    if provider == "spitch":
        return await spitch_provider.synthesize(
            text=text, voice=voice or "", model=model,
            language=language or "en", response_format=response_format,
        )
    if provider == "elevenlabs":
        return await elevenlabs_provider.synthesize(
            text=text, voice=voice, model=model,
            response_format=response_format, language_code=language,
        )
    if provider == "intron":
        return await intron_provider.synthesize(
            text=text, voice=voice, model=model,
            language=language or "en", response_format=response_format,
        )
    raise ValueError(f"Unsupported TTS provider: {provider!r}")
