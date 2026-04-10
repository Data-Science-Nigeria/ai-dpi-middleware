from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.tts.models.openai import OPENAI_INSTRUCTIONS_MODELS, OPENAI_SPEED_MAX, OPENAI_SPEED_MIN
from app.services.tts.models.registry import MODEL_VOICES, PROVIDER_MODELS
from app.services.tts.models.spitch import SPITCH_TTS_LANGUAGES

# Extended format set covers Groq, OpenAI, and Spitch formats
ResponseFormat = Literal[
    "wav", "mp3", "flac", "aac", "opus", "pcm",         # Groq / OpenAI
    "ogg_opus", "webm_opus", "pcm_s16le", "mulaw", "alaw",  # Spitch
]


class TTSRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description=(
            "Text to synthesize. "
            "Orpheus (Groq) models are limited to 200 characters and support inline "
            "vocal-direction tags, e.g. 'Hello! [cheerful] Have a great day.' "
            "OpenAI models accept up to 4096 characters."
        ),
    )
    provider: Literal["groq", "openai", "spitch"] = Field("groq", description="AI provider to use.")
    model: str = Field(
        "playai-tts",
        description=(
            "TTS model. Groq: playai-tts, playai-tts-arabic, "
            "canopylabs/orpheus-v1-english, canopylabs/orpheus-arabic-saudi. "
            "OpenAI: tts-1, tts-1-hd, gpt-4o-mini-tts. "
            "Spitch: legacy."
        ),
    )
    voice: str | None = Field(
        None,
        description=(
            "Voice ID. Required for Spitch. "
            "Groq Orpheus English: Autumn, Diana, Hannah, Austin, Daniel, Troy. "
            "Groq Orpheus Arabic: Fahad, Sultan, Lulwa, Noura. "
            "OpenAI: alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer. "
            "Spitch: see docs.spitch.app/concepts/voices (40 voices across en/ha/ig/yo)."
        ),
    )
    language: str | None = Field(
        None,
        description=(
            "Language code. Required for Spitch (en, ha, ig, yo). "
            "Not used by Groq or OpenAI TTS."
        ),
    )
    response_format: ResponseFormat = Field("wav", description="Audio output format.")

    # OpenAI-only fields
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
        # 1. Provider must support the requested model
        supported_models = PROVIDER_MODELS.get(self.provider, frozenset())
        if self.model not in supported_models:
            raise ValueError(
                f"Provider '{self.provider}' does not support model '{self.model}'. "
                f"Supported models: {sorted(supported_models)}."
            )

        # 2. Voice validation — only checked when the model has a defined voice list
        if self.voice is not None:
            valid_voices = MODEL_VOICES.get(self.model)  # None = no restriction
            if valid_voices is not None and self.voice not in valid_voices:
                raise ValueError(
                    f"Voice '{self.voice}' is not available for model '{self.model}'. "
                    f"Valid voices: {sorted(valid_voices)}."
                )

        # 3. Spitch-specific rules
        if self.provider == "spitch":
            if not self.voice:
                raise ValueError("Spitch TTS requires a `voice`. See docs.spitch.app/concepts/voices.")
            if not self.language:
                raise ValueError(
                    f"Spitch TTS requires a `language`. "
                    f"Supported: {sorted(SPITCH_TTS_LANGUAGES)}."
                )
            if self.language not in SPITCH_TTS_LANGUAGES:
                raise ValueError(
                    f"Language '{self.language}' is not supported by Spitch TTS. "
                    f"Supported: {sorted(SPITCH_TTS_LANGUAGES)}."
                )

        # 4. `instructions` is OpenAI gpt-4o-mini-tts only
        if self.instructions is not None and self.model not in OPENAI_INSTRUCTIONS_MODELS:
            raise ValueError(
                f"`instructions` is only supported by {sorted(OPENAI_INSTRUCTIONS_MODELS)}."
            )

        return self
