"""Service-layer unit tests – chat, STT, TTS, vectordb dispatchers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Chat service dispatcher ───────────────────────────────────────────────────

class TestChatServiceDispatch:

    @pytest.mark.parametrize("provider", ["anthropic", "openai", "groq", "gemini"])
    async def test_dispatches_to_correct_provider(self, provider: str):
        from app.services.chat import main as svc

        mock_path = f"app.services.chat.providers.{provider}.chat"
        with patch(mock_path, new_callable=AsyncMock, return_value="response") as mock_fn:
            result = await svc.chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider=provider,
                model="any-model",
            )
        assert result == "response"
        mock_fn.assert_awaited_once()

    async def test_unknown_provider_raises_value_error(self):
        from app.services.chat import main as svc

        with pytest.raises(ValueError, match="Unsupported provider"):
            await svc.chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider="nonexistent",
                model="model",
            )

    async def test_system_prompt_passed_to_provider(self):
        from app.services.chat import main as svc

        captured = {}

        async def _mock(messages, model, system=None, max_tokens=1024, **_):
            captured["system"] = system
            return "ok"

        with patch("app.services.chat.providers.anthropic.chat", side_effect=_mock):
            await svc.chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider="anthropic",
                model="claude-sonnet-4-6",
                system="Be concise.",
            )

        assert captured["system"] == "Be concise."

    async def test_no_system_prompt_path_in_config(self):
        """When system_prompt_path is None, system stays None."""
        from app.services.chat import main as svc

        captured = {}

        async def _mock(messages, model, system=None, max_tokens=1024, **_):
            captured["system"] = system
            return "ok"

        with patch("app.services.chat.providers.openai.chat", side_effect=_mock):
            await svc.chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider="openai",
                model="gpt-4o",
                system=None,
            )

        assert captured["system"] is None

    async def test_stream_chat_dispatches_to_correct_provider(self):
        from app.services.chat import main as svc

        async def _fake_stream(messages, model, system=None, max_tokens=1024, **_):
            yield "chunk1"
            yield "chunk2"

        with patch("app.services.chat.providers.anthropic.stream_chat", side_effect=_fake_stream):
            chunks = []
            async for chunk in svc.stream_chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider="anthropic",
                model="claude-sonnet-4-6",
            ):
                chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]

    async def test_stream_chat_unknown_provider_raises(self):
        from app.services.chat import main as svc

        with pytest.raises(ValueError, match="Unsupported provider"):
            async for _ in svc.stream_chat(
                messages=[{"role": "user", "content": "Hi"}],
                provider="badprovider",
                model="model",
            ):
                pass


# ── STT service dispatcher ────────────────────────────────────────────────────

class TestSTTServiceDispatch:

    @pytest.mark.parametrize("provider,extra", [
        ("groq", {}),
        ("openai", {}),
        ("deepgram", {}),
        ("spitch", {"language": "en", "special_words": None, "timestamp": "none"}),
        ("intron", {"language": "ha", "special_words": None, "timestamp": "none"}),
    ])
    async def test_dispatches_to_correct_provider(self, provider: str, extra: dict):
        from app.services.stt import main as svc

        mock_result = {"text": "hello", "language": "en", "duration": 1.0}
        mock_path = f"app.services.stt.providers.{provider}.transcribe"
        with patch(mock_path, new_callable=AsyncMock, return_value=mock_result) as mock_fn:
            result = await svc.transcribe(
                file_bytes=b"\x00" * 100,
                filename="test.wav",
                content_type="audio/wav",
                provider=provider,
                model="any-model",
                language=extra.get("language"),
                prompt=None,
                special_words=extra.get("special_words"),
                timestamp=extra.get("timestamp", "none"),
            )
        assert result["text"] == "hello"
        mock_fn.assert_awaited_once()

    async def test_unknown_provider_raises(self):
        from app.services.stt import main as svc

        with pytest.raises(ValueError, match="Unsupported STT provider"):
            await svc.transcribe(
                file_bytes=b"bytes",
                filename="test.wav",
                content_type="audio/wav",
                provider="badprovider",
                model="model",
            )


# ── TTS service dispatcher ────────────────────────────────────────────────────

class TestTTSServiceDispatch:

    @pytest.mark.parametrize("provider", ["groq", "openai", "spitch", "elevenlabs", "intron"])
    async def test_dispatches_to_correct_provider(self, provider: str):
        from app.services.tts import main as svc

        fake_audio = b"audio-bytes"
        mock_path = f"app.services.tts.providers.{provider}.synthesize"
        with patch(mock_path, new_callable=AsyncMock, return_value=fake_audio) as mock_fn:
            result = await svc.synthesize(
                text="Hello",
                voice="voice-id",
                model="any-model",
                response_format="wav",
                provider=provider,
                language="en",
            )
        assert result == fake_audio
        mock_fn.assert_awaited_once()

    async def test_unknown_provider_raises(self):
        from app.services.tts import main as svc

        with pytest.raises(ValueError, match="Unsupported TTS provider"):
            await svc.synthesize(
                text="Hello",
                voice=None,
                model="model",
                response_format="wav",
                provider="badprovider",
            )


# ── VectorDB service dispatcher ───────────────────────────────────────────────

class TestVectorDBService:

    async def test_add_delegates_to_provider(self):
        from app.services.vectordb import main as svc

        mock_provider = MagicMock()
        mock_provider.add = AsyncMock()

        with patch.object(svc, "_provider", return_value=mock_provider):
            await svc.add(
                collection_name="test_col",
                embeddings=[[0.1, 0.2, 0.3]],
                documents=["doc1"],
            )

        mock_provider.add.assert_awaited_once_with(
            collection_name="test_col",
            embeddings=[[0.1, 0.2, 0.3]],
            documents=["doc1"],
            meta_data=None,
        )

    async def test_retrieve_delegates_to_provider(self):
        from app.services.vectordb import main as svc

        mock_provider = MagicMock()
        mock_provider.retrieve = AsyncMock(return_value="doc content")

        with patch.object(svc, "_provider", return_value=mock_provider):
            result = await svc.retrieve(
                embedding=[0.1, 0.2],
                collection_name="test_col",
            )

        assert result == "doc content"

    def test_unsupported_provider_raises(self):
        from app.services.vectordb import main as svc

        with patch("app.config.get_config", return_value={
            "llm": {"vector_database": {"provider": "chromadb"}}
        }):
            with pytest.raises(ValueError, match="Unsupported vector_database provider"):
                svc._provider()

    @pytest.mark.parametrize("provider_name", ["weaviate", "pinecone", "qdrant"])
    def test_all_providers_resolvable(self, provider_name: str):
        from app.services.vectordb import main as svc

        cfg = {"llm": {"vector_database": {"provider": provider_name}}}
        with patch("app.config.get_config", return_value=cfg):
            p = svc._provider()
            assert p is not None


# ── Translate prompt builder ──────────────────────────────────────────────────

class TestTranslatePromptBuilder:

    def test_prompt_with_source(self):
        from app.routers.v1.translate_route import _build_prompt
        prompt = _build_prompt("Hello", "en", "fr")
        assert "from en" in prompt
        assert "fr" in prompt
        assert "Hello" in prompt

    def test_prompt_auto_detect_when_no_source(self):
        from app.routers.v1.translate_route import _build_prompt
        prompt = _build_prompt("Hello", None, "es")
        assert "auto" in prompt.lower() or "detect" in prompt.lower()
        assert "es" in prompt
        assert "Hello" in prompt

    def test_prompt_instructs_no_explanation(self):
        from app.routers.v1.translate_route import _build_prompt
        prompt = _build_prompt("Hello", None, "yo")
        assert "no explanation" in prompt.lower() or "only the translated" in prompt.lower()


# ── Embedding service ─────────────────────────────────────────────────────────

class TestEmbeddingService:

    async def test_delegates_to_openai_provider(self):
        from app.services.embedding import main as svc

        fake_embedding = [0.1] * 1536
        with patch("app.services.embedding.providers.openai.get_embedding",
                   new_callable=AsyncMock, return_value=fake_embedding) as mock_fn:
            result = await svc.get_embedding("some text")

        assert result == fake_embedding
        mock_fn.assert_awaited_once()

    async def test_uses_configured_model(self):
        from app.services.embedding import main as svc

        captured = {}

        async def _mock(text, model):
            captured["model"] = model
            return [0.0] * 128

        with patch("app.services.embedding.providers.openai.get_embedding", side_effect=_mock):
            await svc.get_embedding("text")

        assert captured["model"] == "text-embedding-3-small"
