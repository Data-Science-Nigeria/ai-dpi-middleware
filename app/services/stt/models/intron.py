"""Intron (Sahara) STT model registry.

Intron builds African-language speech models under the Sahara project.
Languages span West, East, and Southern Africa.
"""

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "intron": frozenset({
        "sahara-v1",
    }),
}

# BCP-47 language codes supported by Intron Sahara STT
INTRON_STT_LANGUAGES: frozenset[str] = frozenset({
    "sw",   # Swahili
    "ha",   # Hausa
    "yo",   # Yoruba
    "ig",   # Igbo
    "am",   # Amharic
    "so",   # Somali
    "zu",   # Zulu
    "xh",   # Xhosa
    "af",   # Afrikaans
    "wo",   # Wolof
    "ff",   # Fulah / Fula
    "en",   # English (African-accented)
})

DEFAULT_MODEL = "sahara-v1"
