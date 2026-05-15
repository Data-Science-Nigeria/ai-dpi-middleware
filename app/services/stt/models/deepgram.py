"""Deepgram STT model registry.

nova-3  — latest, highest accuracy, 100+ languages
nova-2  — reliable, 30+ languages
enhanced — enhanced accuracy, slower
base    — fastest, lower accuracy
"""

PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "deepgram": frozenset({
        "nova-3",
        "nova-2",
        "enhanced",
        "base",
    }),
}

# Languages supported by nova-3 (superset; nova-2/enhanced/base support a subset)
DEEPGRAM_LANGUAGES: frozenset[str] = frozenset({
    "af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs",
    "bg", "ca", "zh", "zh-CN", "zh-TW", "hr", "cs", "da", "nl",
    "en", "et", "fi", "fr", "gl", "ka", "de", "el", "gu", "ha",
    "he", "hi", "hu", "is", "id", "it", "ja", "kn", "kk", "km",
    "ko", "ku", "ky", "lo", "lv", "lt", "lb", "mk", "ms", "ml",
    "mt", "mn", "my", "ne", "no", "ps", "fa", "pl", "pt", "pt-BR",
    "pa", "ro", "ru", "sr", "si", "sk", "sl", "so", "es", "sw",
    "sv", "tl", "tg", "ta", "te", "th", "tr", "tk", "uk", "ur",
    "uz", "vi", "cy", "yo",
})

DEFAULT_MODEL = "nova-3"
