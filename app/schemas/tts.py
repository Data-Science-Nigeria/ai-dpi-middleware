from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.tts.models.groq import ResponseFormat
from app.services.tts.models.openai import OPENAI_INSTRUCTIONS_MODELS, OPENAI_SPEED_MAX, OPENAI_SPEED_MIN
from app.services.tts.models.registry import MODEL_VOICES, PROVIDER_MODELS


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
    provider: Literal["groq", "openai"] = Field("groq", description="AI provider to use.")
    model: str = Field(
        "playai-tts",
        description=(
            "TTS model. Groq: playai-tts, playai-tts-arabic, "
            "canopylabs/orpheus-v1-english, canopylabs/orpheus-arabic-saudi. "
            "OpenAI: tts-1, tts-1-hd, gpt-4o-mini-tts."
        ),
    )
    voice: str | None = Field(
        None,
        description=(
            "Voice ID. Defaults to the model's standard voice when omitted. "
            "Groq Orpheus English: Autumn, Diana, Hannah, Austin, Daniel, Troy. "
            "Groq Orpheus Arabic: Fahad, Sultan, Lulwa, Noura. "
            "OpenAI: alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer."
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
        description=(
            f"Optional prompt shaping the voice delivery. "
            f"Only supported by: {sorted(OPENAI_INSTRUCTIONS_MODELS)}."
        ),
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

        # 2. If a voice was supplied, it must be valid for the model
        if self.voice is not None:
            valid_voices = MODEL_VOICES.get(self.model, frozenset())
            if self.voice not in valid_voices:
                raise ValueError(
                    f"Voice '{self.voice}' is not available for model '{self.model}'. "
                    f"Valid voices: {sorted(valid_voices)}."
                )

        # 3. `instructions` is OpenAI gpt-4o-mini-tts only
        if self.instructions is not None and self.model not in OPENAI_INSTRUCTIONS_MODELS:
            raise ValueError(
                f"`instructions` is only supported by {sorted(OPENAI_INSTRUCTIONS_MODELS)}."
            )

        return self
