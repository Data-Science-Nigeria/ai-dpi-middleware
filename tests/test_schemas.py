"""Pydantic schema validation – unit tests with no HTTP layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ai import ChatRequest, ChatResponse, Message
from app.schemas.stt import TranscriptionResponse
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.schemas.tts import TTSRequest


# ── Message ───────────────────────────────────────────────────────────────────

class TestMessage:
    def test_user_role_valid(self):
        m = Message(role="user", content="Hello")
        assert m.role == "user"

    def test_assistant_role_valid(self):
        m = Message(role="assistant", content="Hi there")
        assert m.role == "assistant"

    def test_system_role_rejected(self):
        with pytest.raises(ValidationError):
            Message(role="system", content="You are a bot")

    def test_empty_role_rejected(self):
        with pytest.raises(ValidationError):
            Message(role="", content="Hello")


# ── ChatRequest ───────────────────────────────────────────────────────────────

class TestChatRequest:
    def test_valid_anthropic_request(self):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="anthropic",
            model="claude-sonnet-4-6",
        )
        assert r.provider == "anthropic"
        assert r.model == "claude-sonnet-4-6"

    def test_model_resolved_when_omitted(self):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="anthropic",
        )
        assert r.model == "claude-sonnet-4-6"

    def test_groq_default_model_resolved(self):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="groq",
        )
        assert r.model == "llama-3.3-70b-versatile"

    def test_gemini_default_model_resolved(self):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="gemini",
        )
        assert r.model == "gemini-2.5-flash"

    def test_openai_default_model_resolved(self):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="openai",
        )
        assert r.model == "gpt-4o"

    def test_incompatible_model_raises(self):
        with pytest.raises(ValidationError, match="does not support"):
            ChatRequest(
                messages=[{"role": "user", "content": "Hi"}],
                provider="anthropic",
                model="gpt-4o",
            )

    def test_unknown_provider_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[{"role": "user", "content": "Hi"}],
                provider="fakeprovider",
            )

    def test_empty_messages_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[], provider="anthropic")

    def test_max_tokens_lower_bound(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[{"role": "user", "content": "Hi"}],
                provider="anthropic",
                model="claude-sonnet-4-6",
                max_tokens=0,
            )

    def test_max_tokens_upper_bound(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[{"role": "user", "content": "Hi"}],
                provider="anthropic",
                model="claude-sonnet-4-6",
                max_tokens=99999,
            )

    @pytest.mark.parametrize("model", [
        "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"
    ])
    def test_all_anthropic_models_valid(self, model: str):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="anthropic", model=model,
        )
        assert r.model == model

    @pytest.mark.parametrize("model", [
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
        "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro",
        "gemini-1.5-flash", "gemini-1.5-flash-8b",
    ])
    def test_all_gemini_models_valid(self, model: str):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="gemini", model=model,
        )
        assert r.model == model

    @pytest.mark.parametrize("model", [
        "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "groq/compound", "groq/compound-mini",
        "mixtral-8x7b-32768", "gemma2-9b-it", "qwen/qwen3-32b",
    ])
    def test_all_groq_models_valid(self, model: str):
        r = ChatRequest(
            messages=[{"role": "user", "content": "Hi"}],
            provider="groq", model=model,
        )
        assert r.model == model


# ── TranslateRequest ──────────────────────────────────────────────────────────

class TestTranslateRequest:
    def test_minimal_valid_request(self):
        r = TranslateRequest(text="Hello", target_language="fr")
        assert r.provider == "anthropic"  # default
        assert r.source_language is None

    def test_text_too_short_raises(self):
        with pytest.raises(ValidationError):
            TranslateRequest(text="", target_language="fr")

    def test_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            TranslateRequest(text="x" * 10001, target_language="fr")

    def test_max_tokens_defaults_to_4096(self):
        r = TranslateRequest(text="Hello", target_language="fr")
        assert r.max_tokens == 4096

    def test_invalid_provider_raises(self):
        with pytest.raises(ValidationError):
            TranslateRequest(text="Hello", target_language="fr", provider="fakeprovider")

    @pytest.mark.parametrize("provider", ["anthropic", "openai", "groq", "gemini"])
    def test_all_providers_valid(self, provider: str):
        r = TranslateRequest(text="Hello", target_language="fr", provider=provider)
        assert r.provider == provider


# ── TTSRequest ────────────────────────────────────────────────────────────────

class TestTTSRequest:
    def test_valid_groq_request(self):
        r = TTSRequest(text="Hello", provider="groq", model="playai-tts", voice="Fritz-PlayAI")
        assert r.provider == "groq"

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="", provider="groq", model="playai-tts")

    def test_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="x" * 5001, provider="groq", model="playai-tts")

    def test_incompatible_model_raises(self):
        with pytest.raises(ValidationError, match="does not support"):
            TTSRequest(text="Hello", provider="groq", model="tts-1")

    def test_spitch_without_voice_raises(self):
        with pytest.raises(ValidationError, match="voice"):
            TTSRequest(
                text="Hello", provider="spitch", model="legacy", language="en"
            )

    def test_spitch_without_language_raises(self):
        with pytest.raises(ValidationError, match="language"):
            TTSRequest(
                text="Hello", provider="spitch", model="legacy", voice="en-male-1"
            )

    def test_spitch_unsupported_language_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(
                text="Hello", provider="spitch", model="legacy",
                voice="zh-male-1", language="zh",
            )

    def test_intron_without_language_raises(self):
        with pytest.raises(ValidationError, match="language"):
            TTSRequest(
                text="Hello", provider="intron", model="sahara-tts-v1", voice="en-female-1"
            )

    def test_instructions_on_non_supported_model_raises(self):
        with pytest.raises(ValidationError, match="instructions"):
            TTSRequest(
                text="Hello", provider="openai", model="tts-1",
                voice="alloy", instructions="Speak slowly",
            )

    def test_instructions_on_gpt4o_mini_tts_valid(self):
        r = TTSRequest(
            text="Hello", provider="openai", model="gpt-4o-mini-tts",
            voice="alloy", instructions="Speak slowly",
        )
        assert r.instructions == "Speak slowly"

    def test_speed_below_min_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(
                text="Hello", provider="openai", model="tts-1", voice="alloy", speed=0.1
            )

    def test_speed_above_max_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(
                text="Hello", provider="openai", model="tts-1", voice="alloy", speed=10.0
            )

    @pytest.mark.parametrize("fmt", [
        "wav", "mp3", "flac", "aac", "opus", "pcm",
        "ogg_opus", "webm_opus", "pcm_s16le", "mulaw", "alaw",
    ])
    def test_all_response_formats_valid(self, fmt: str):
        r = TTSRequest(
            text="Hello", provider="groq", model="playai-tts",
            voice="Fritz-PlayAI", response_format=fmt,
        )
        assert r.response_format == fmt

    def test_invalid_response_format_raises(self):
        with pytest.raises(ValidationError):
            TTSRequest(
                text="Hello", provider="groq", model="playai-tts",
                voice="Fritz-PlayAI", response_format="mp5",
            )


# ── TranscriptionResponse ─────────────────────────────────────────────────────

class TestTranscriptionResponse:
    def test_minimal_valid(self):
        r = TranscriptionResponse(text="Hello", provider="groq", model="whisper-large-v3-turbo")
        assert r.language is None
        assert r.duration is None

    def test_full_response(self):
        r = TranscriptionResponse(
            text="Hello world", language="en", duration=2.5,
            provider="deepgram", model="nova-3"
        )
        assert r.duration == 2.5


# ── ChatResponse ──────────────────────────────────────────────────────────────

class TestChatResponse:
    def test_valid(self):
        r = ChatResponse(reply="Hello", provider="anthropic", model="claude-sonnet-4-6")
        assert r.reply == "Hello"
