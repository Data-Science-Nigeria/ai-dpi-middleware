PROVIDER_MODELS: dict[str, frozenset[str]] = {
    "gemini": frozenset({
        # Gemini 2.5 series (stable)
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # Gemini 2.0 series
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        # Gemini 1.5 series (legacy, still available)
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    }),
}

DEFAULT_MODEL = "gemini-2.5-flash"
