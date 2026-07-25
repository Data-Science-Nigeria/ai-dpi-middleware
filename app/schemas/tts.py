from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.tts.models.elevenlabs import ELEVENLABS_LANGUAGES
from app.services.tts.models.intron import INTRON_TTS_LANGUAGES
from app.services.tts.models.openai import OPENAI_INSTRUCTIONS_MODELS, OPENAI_SPEED_MAX, OPENAI_SPEED_MIN
from app.services.tts.models.registry import MODEL_VOICES, PROVIDER_MODELS
from app.services.tts.models.spitch import SPITCH_TTS_LANGUAGES

ResponseFormat = Literal[
    "wav", "mp3", "flac", "aac", "opus", "pcm",
    "ogg_opus", "webm_opus", "pcm_s16le", "mulaw", "alaw",
]


class TTSRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description=(
            "Text to synthesize. "
            "Orpheus (Groq) models are limited to 200 characters and support inline "
            "vocal-direction tags, e.g. 'Hello! [cheerful] Have a great day.' "
            "OpenAI and ElevenLabs accept up to 5000 characters."
        ),
    )
    provider: Literal["groq", "openai", "spitch", "elevenlabs", "intron"] = Field(
        "groq",
        description="TTS provider. elevenlabs: 32 languages. intron: African languages. spitch: West/East African languages.",
    )
    model: str = Field(
        "playai-tts",
        description=(
            "TTS model. "
            "Groq: playai-tts, playai-tts-arabic, canopylabs/orpheus-v1-english, canopylabs/orpheus-arabic-saudi. "
            "OpenAI: tts-1, tts-1-hd, gpt-4o-mini-tts. "
            "Spitch: legacy. "
            "ElevenLabs: eleven_multilingual_v2 (default), eleven_flash_v2_5, eleven_turbo_v2_5, eleven_monolingual_v1. "
            "Intron: sahara-tts-v1."
        ),
    )
    voice: str | None = Field(
        None,
        description=(
            "Voice ID. Required for Spitch and Intron. "
            "Groq Orpheus English: Autumn, Diana, Hannah, Austin, Daniel, Troy. "
            "Groq Orpheus Arabic: Fahad, Sultan, Lulwa, Noura. "
            "OpenAI: alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer. "
            "ElevenLabs: Rachel, Bella, Antoni, Elli, Josh, Arnold, Adam, Sam (and more). Defaults to Rachel. "
            "Spitch: see docs.spitch.app/concepts/voices. "
            "Intron: <lang>-male-1 or <lang>-female-1, e.g. sw-female-1."
        ),
    )
    language: str | None = Field(
        None,
        description=(
            "BCP-47 language code. "
            "Required for Spitch (en, ha, ig, yo) and Intron (sw, ha, yo, ig, am, en). "
            "Optional for ElevenLabs – omit for auto-detection from text. "
            "Not used by Groq or OpenAI TTS."
        ),
    )
    response_format: ResponseFormat = Field("wav", description="Audio output format.")

    # OpenAI-only
    speed: float = Field(
        1.0,
        ge=OPENAI_SPEED_MIN,
        le=OPENAI_SPEED_MAX,
        description=f"Playback speed ({OPENAI_SPEED_MIN}–{OPENAI_SPEED_MAX}). OpenAI only.",
    )
    instructions: str | None = Field(
        None,
        description=f"Voice delivery prompt. Only supported by: {sorted(OPENAI_INSTRUCTIONS_MODELS)}.",
    )

    @model_validator(mode="after")
    def validate_provider_model_voice(self) -> TTSRequest:
        self._validate_model_supported()
        self._validate_voice()
        self._validate_spitch()
        self._validate_intron()
        self._validate_elevenlabs_language()
        self._validate_instructions()
        return self

    def _validate_model_supported(self) -> None:
        # 1. Provider must support the requested model
        supported_models = PROVIDER_MODELS.get(self.provider, frozenset())
        if self.model not in supported_models:
            raise ValueError(
                f"Provider '{self.provider}' does not support model '{self.model}'. "
                f"Supported models: {sorted(supported_models)}."
            )

    def _validate_voice(self) -> None:
        # 2. Voice validation – only for models with a defined voice list
        if self.voice is None:
            return
        valid_voices = MODEL_VOICES.get(self.model)
        if valid_voices is not None and self.voice not in valid_voices:
            raise ValueError(
                f"Voice '{self.voice}' is not valid for model '{self.model}'. "
                f"Valid voices: {sorted(valid_voices)}."
            )

    def _validate_spitch(self) -> None:
        # 3. Spitch rules
        if self.provider != "spitch":
            return
        if not self.voice:
            raise ValueError("Spitch TTS requires a `voice`. See docs.spitch.app/concepts/voices.")
        if not self.language:
            raise ValueError(f"Spitch TTS requires a `language`. Supported: {sorted(SPITCH_TTS_LANGUAGES)}.")
        if self.language not in SPITCH_TTS_LANGUAGES:
            raise ValueError(
                f"Language '{self.language}' is not supported by Spitch TTS. "
                f"Supported: {sorted(SPITCH_TTS_LANGUAGES)}."
            )

    def _validate_intron(self) -> None:
        # 4. Intron rules
        if self.provider != "intron":
            return
        if not self.language:
            raise ValueError(f"Intron TTS requires a `language`. Supported: {sorted(INTRON_TTS_LANGUAGES)}.")
        if self.language not in INTRON_TTS_LANGUAGES:
            raise ValueError(
                f"Language '{self.language}' is not supported by Intron TTS. "
                f"Supported: {sorted(INTRON_TTS_LANGUAGES)}."
            )

    def _validate_elevenlabs_language(self) -> None:
        # 5. ElevenLabs language validation (optional – only when provided)
        if self.provider == "elevenlabs" and self.language and self.language not in ELEVENLABS_LANGUAGES:
            raise ValueError(
                f"Language '{self.language}' is not supported by ElevenLabs. "
                f"Supported: {sorted(ELEVENLABS_LANGUAGES)}."
            )

    def _validate_instructions(self) -> None:
        # 6. `instructions` is OpenAI gpt-4o-mini-tts only
        if self.instructions is not None and self.model not in OPENAI_INSTRUCTIONS_MODELS:
            raise ValueError(f"`instructions` is only supported by {sorted(OPENAI_INSTRUCTIONS_MODELS)}.")
