from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.tts.models.groq import (
    GroqTTSModel,
    MODEL_VOICES,
    PROVIDER_MODELS,
    ResponseFormat,
)


class TTSRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description=(
            "Text to synthesize. Orpheus models are limited to 200 characters. "
            "The English Orpheus model supports inline vocal-direction tags, e.g. "
            "'Hello! [cheerful] Have a great day.'"
        ),
    )
    model: GroqTTSModel = Field("playai-tts", description="TTS model to use.")
    voice: str | None = Field(
        None,
        description=(
            "Voice ID. Defaults to the model's standard voice when omitted. "
            "Orpheus English voices: Autumn, Diana, Hannah, Austin, Daniel, Troy. "
            "Orpheus Arabic voices: Fahad, Sultan, Lulwa, Noura."
        ),
    )
    response_format: ResponseFormat = Field("wav", description="Audio output format.")
    provider: Literal["groq"] = Field("groq", description="AI provider to use.")

    @model_validator(mode="after")
    def validate_provider_and_voice(self) -> TTSRequest:
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

        return self
