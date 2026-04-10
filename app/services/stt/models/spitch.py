"""Spitch STT model definitions."""

from typing import Literal

SpitchSTTModel = Literal[
    "legacy",    # Standard transcription (default)
    "mansa_v1",  # Enhanced accuracy for African-accented English; supports timestamps
]

SpitchLanguage = Literal["en", "yo", "ha", "ig", "am"]

SpitchTimestamp = Literal["none", "sentence", "word"]

# Only mansa_v1 supports timestamp granularity
SPITCH_TIMESTAMP_MODELS: frozenset[str] = frozenset({"mansa_v1"})

# Spitch only accepts these four formats
SPITCH_ACCEPTED_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".wav", ".m4a", ".ogg"})

SPITCH_MAX_FILE_MB = 25

# Languages supported by Spitch STT
SPITCH_LANGUAGES: frozenset[str] = frozenset(SpitchLanguage.__args__)  # type: ignore[attr-defined]

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "spitch": frozenset(SpitchSTTModel.__args__),  # type: ignore[attr-defined]
}

DEFAULT_MODEL = "legacy"
