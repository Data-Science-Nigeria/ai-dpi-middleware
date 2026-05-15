"""Intron (Sahara) TTS model registry."""

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "intron": frozenset({
        "sahara-tts-v1",
    }),
}

MODEL_VOICES: dict[str, frozenset[str]] = {
    # Intron voices are language-scoped; validation is done in the provider.
    # We leave this open (no frozenset restriction) so unknown voices pass schema
    # validation and are caught by the API with a clear error message.
}

DEFAULT_VOICE: dict[str, str] = {
    "sahara-tts-v1": "default",
}

# Language → available voices
INTRON_VOICES: dict[str, frozenset[str]] = {
    "sw": frozenset({"sw-male-1", "sw-female-1"}),
    "ha": frozenset({"ha-male-1", "ha-female-1"}),
    "yo": frozenset({"yo-male-1", "yo-female-1"}),
    "ig": frozenset({"ig-male-1", "ig-female-1"}),
    "am": frozenset({"am-male-1", "am-female-1"}),
    "en": frozenset({"en-male-1", "en-female-1"}),
}

INTRON_TTS_LANGUAGES: frozenset[str] = frozenset(INTRON_VOICES.keys())
