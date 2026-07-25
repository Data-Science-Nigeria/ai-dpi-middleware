"""Groq TTS model definitions — Orpheus by Canopy Labs + PlayAI."""

from typing import Literal, get_args

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

# PlayAI models (general-purpose, no character cap)
PlayAIModel = Literal[
    "playai-tts",
    "playai-tts-arabic",
]

# Orpheus models (max 200 chars per request, English supports vocal directions)
OrpheusModel = Literal[
    "canopylabs/orpheus-v1-english",
    "canopylabs/orpheus-arabic-saudi",
]

# Nested Literals flatten (PEP 586): GroqTTSModel.__args__ still yields the
# four model-ID strings, without re-listing them here.
GroqTTSModel = Literal[PlayAIModel, OrpheusModel]

# Canonical Orpheus model IDs — reused by every runtime lookup table below so
# the strings are not duplicated. (PEP 586 forbids variables inside Literal[...],
# so the OrpheusModel definition above keeps the only other literal copies.)
ORPHEUS_V1_ENGLISH = "canopylabs/orpheus-v1-english"
ORPHEUS_ARABIC_SAUDI = "canopylabs/orpheus-arabic-saudi"

# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------

# Orpheus English voices  (model: canopylabs/orpheus-v1-english)
OrpheusEnglishVoice = Literal[
    "Autumn", "Diana", "Hannah",   # Female
    "Austin", "Daniel", "Troy",    # Male
]

# Orpheus Arabic voices  (model: canopylabs/orpheus-arabic-saudi)
OrpheusArabicVoice = Literal[
    "Fahad", "Sultan",             # Male
    "Lulwa", "Noura",              # Female
]

# PlayAI voices  (models: playai-tts / playai-tts-arabic)
PlayAIVoice = Literal[
    "Aaliyah", "Adelaide", "Angelo", "Arsenio", "Barbra", "Briggs",
    "Calum", "Celeste", "Chandra", "Chip", "Cillian", "Deedee",
    "Dexter", "Edmund", "Evangeline", "Felicity", "Gideon", "Hank",
    "Hera", "Jedidiah", "Kendrick", "Kitty", "Quinn", "Tara", "Thunder",
]

# ---------------------------------------------------------------------------
# Response formats
# ---------------------------------------------------------------------------

ResponseFormat = Literal["wav", "mp3", "flac", "aac", "opus", "pcm"]

# ---------------------------------------------------------------------------
# Orpheus constraints
# ---------------------------------------------------------------------------

# Orpheus models cap input at 200 characters per request
ORPHEUS_MAX_CHARS = 200

# Orpheus models that support vocal-direction tags (English only)
ORPHEUS_VOCAL_DIRECTION_MODELS: frozenset[str] = frozenset({
    ORPHEUS_V1_ENGLISH,
})

ORPHEUS_MODELS: frozenset[str] = frozenset(get_args(OrpheusModel))

# ---------------------------------------------------------------------------
# Vocal directions (English model only)
#
# Embed these tags anywhere in the input string to shape delivery, e.g.:
#   "Good morning! [cheerful] Have a wonderful day."
# Multiple tags may appear in a single utterance.
# ---------------------------------------------------------------------------

VocalDirection = Literal[
    # Emotion / mood
    "[cheerful]",
    "[sad]",
    "[angry]",
    "[fearful]",
    "[disgusted]",
    "[surprised]",
    # Conversational register
    "[friendly]",
    "[casual]",
    "[authoritatively]",
    "[formally]",
    # Vocal quality / delivery
    "[whisper]",
    "[gravelly whisper]",
    "[rapid babbling]",
    "[laughing]",
    "[giggling]",
    "[sighing]",
    "[crying]",
    "[screaming]",
]

VOCAL_DIRECTIONS: list[str] = list(VocalDirection.__args__)  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Model → default voice
# ---------------------------------------------------------------------------

DEFAULT_VOICE: dict[str, str] = {
    "playai-tts": "Tara",
    "playai-tts-arabic": "Noura",
    ORPHEUS_V1_ENGLISH: "Tara",
    ORPHEUS_ARABIC_SAUDI: "Noura",
}

# ---------------------------------------------------------------------------
# Validation lookup tables
# ---------------------------------------------------------------------------

# Provider → set of supported model IDs
PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "groq": frozenset(GroqTTSModel.__args__),  # type: ignore[attr-defined]
}

# Model → set of valid voice IDs (case-insensitive keys stored as-is)
MODEL_VOICES: dict[str, frozenset[str]] = {
    "playai-tts":         frozenset(PlayAIVoice.__args__),          # type: ignore[attr-defined]
    "playai-tts-arabic":  frozenset(PlayAIVoice.__args__),          # type: ignore[attr-defined]
    ORPHEUS_V1_ENGLISH:   frozenset(OrpheusEnglishVoice.__args__),  # type: ignore[attr-defined]
    ORPHEUS_ARABIC_SAUDI: frozenset(OrpheusArabicVoice.__args__),   # type: ignore[attr-defined]
}
