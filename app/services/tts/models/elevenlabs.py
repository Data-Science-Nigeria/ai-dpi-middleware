"""ElevenLabs TTS model registry.

eleven_multilingual_v2  – highest quality, 32 languages (recommended)
eleven_flash_v2_5       – ultra-low latency, 32 languages
eleven_turbo_v2_5       – low latency, 32 languages
eleven_monolingual_v1   – English only, legacy
"""

# Pre-made voice IDs (name → ElevenLabs voice_id)
# Full list at: https://api.elevenlabs.io/v1/voices
ELEVENLABS_VOICES: frozenset[str] = frozenset({
    "Rachel", "Drew", "Clyde", "Paul", "Domi", "Dave", "Fin",
    "Bella", "Antoni", "Thomas", "Charlie", "George", "Emily",
    "Elli", "Callum", "Patrick", "Harry", "Liam", "Dorothy",
    "Josh", "Arnold", "Charlotte", "Matilda", "Matthew", "James",
    "Joseph", "Jeremy", "Michael", "Ethan", "Gigi", "Freya",
    "Grace", "Daniel", "Serena", "Adam", "Nicole", "Jessie",
    "Ryan", "Sam", "Glinda", "Giovanni", "Mimi",
})

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "elevenlabs": frozenset({
        "eleven_multilingual_v2",
        "eleven_flash_v2_5",
        "eleven_turbo_v2_5",
        "eleven_monolingual_v1",
    }),
}

MODEL_VOICES: dict[str, frozenset[str]] = dict.fromkeys(
    # All ElevenLabs models share the same (immutable) voice pool
    PROVIDER_MODELS["elevenlabs"], ELEVENLABS_VOICES
)

DEFAULT_VOICE: dict[str, str] = {
    "eleven_multilingual_v2": "Rachel",
    "eleven_flash_v2_5": "Rachel",
    "eleven_turbo_v2_5": "Rachel",
    "eleven_monolingual_v1": "Rachel",
}

# 32 languages supported by multilingual models
ELEVENLABS_LANGUAGES: frozenset[str] = frozenset({
    "en", "ja", "zh", "de", "hi", "fr", "ko", "pt", "it", "es",
    "id", "nl", "tr", "fil", "pl", "sv", "bg", "ro", "ar", "cs",
    "el", "fi", "hr", "ms", "sk", "da", "ta", "uk", "ru", "hu",
    "no", "vi",
})

# Output formats accepted by the ElevenLabs API
ELEVENLABS_OUTPUT_FORMATS: frozenset[str] = frozenset({
    "mp3_44100_128",
    "mp3_44100_64",
    "pcm_16000",
    "pcm_22050",
    "pcm_24000",
    "pcm_44100",
    "ulaw_8000",
})

# Map from our common format names to ElevenLabs output_format strings
FORMAT_MAP: dict[str, str] = {
    "mp3":        "mp3_44100_128",
    "pcm":        "pcm_24000",
    "wav":        "pcm_44100",
    "ulaw":       "ulaw_8000",
    "mulaw":      "ulaw_8000",
}
