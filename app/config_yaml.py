"""Loader for default_config.yaml.

Values in the YAML that match the pattern [ENV_VAR_NAME] are substituted
with the corresponding OS environment variable at load time.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic models mirroring the YAML structure
# ---------------------------------------------------------------------------

class ChromaDBConfig(BaseModel):
    path: str = "./chroma_db"
    pdf_collection: str = "pdf_paragraphs"


class EmbeddingConfig(BaseModel):
    model_path: str = "./model-s/African-Cross-Lingua-Embeddings-Model"
    cross_encoder_path: str = "./model-s/ms-marco-MiniLM-L-6-v2"


class DocumentConfig(BaseModel):
    pdf_folder: str = "./data/documents"
    min_paragraph_length: int = 50
    chunk_overlap_sentences: int = 3
    image_folder: str = "./data/images"
    audio_folder: str = "./data/audio"
    enable_pdf_ocr: bool = True
    extract_tables: bool = False


class LLMConfig(BaseModel):
    model_name: str = "qwen/qwen2.5-7b-instruct"
    api_key: str | None = None
    backend: str = "local"
    max_context_length: int = 131072
    max_new_tokens: int = 8192
    temperature: float = 0.9
    top_p: float = 0.95
    repetition_penalty: float = 1.05
    stop: list[str] = Field(default_factory=lambda: ["<|im_end|>", "<|end_of_text|>"])


class SpeechConfig(BaseModel):
    whisper_model_path: str = "./model-s/whisper-small"
    sampling_rate: int = 16000
    confidence_threshold: float = 0.6
    use_segmentation: bool = True
    language: str = "en"
    device: str = "auto"
    max_file_size_mb: int = 50


class RetrievalPreset(BaseModel):
    top_k: int
    rerank_k: int


class RAGConfig(BaseModel):
    minimum_relevance_threshold: float = 0.5
    top_k: int = 10
    rerank_k: int = 3
    retrieval_presets: dict[str, RetrievalPreset] = Field(default_factory=dict)


class ChatConfig(BaseModel):
    history_limit: int = 10
    session_ttl_hours: int = 24


class SmartChatConfig(BaseModel):
    confidence_threshold: float = 0.7


class RateLimitsConfig(BaseModel):
    storage_uri: str = "memory://"
    global_default: int = 100
    upload_single: int = 10
    upload_multi: int = 5
    query_direct: int = 30
    query_rag: int = 30
    session_operations: int = 60


class UploadConfig(BaseModel):
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = Field(default_factory=list)


class SecurityConfig(BaseModel):
    enable_content_sanitization: bool = True
    strict_sanitization_mode: bool = False
    rate_limits: RateLimitsConfig = Field(default_factory=RateLimitsConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    allowed_departments: list[str] = Field(default_factory=list)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/all.log"


class ImageConfig(BaseModel):
    min_paragraph_length: int = 50
    lang: str = "eng"
    tesseract_path: str | None = None
    enable_preprocessing: bool = True
    enable_quality_validation: bool = True
    quality_threshold: float = 0.2


class JWTConfig(BaseModel):
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


class AppConfig(BaseModel):
    chroma_db: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    document: DocumentConfig = Field(default_factory=DocumentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)
    smart_chat: SmartChatConfig = Field(default_factory=SmartChatConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)


# ---------------------------------------------------------------------------
# Env-var substitution
# ---------------------------------------------------------------------------

_ENV_PLACEHOLDER = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively replace [VAR_NAME] placeholders with env var values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
                    return os.environ.get(match.group(1)) or match.group(0)
        return _ENV_PLACEHOLDER.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "default_config.yaml"


@lru_cache(maxsize=1)
def get_yaml_config() -> AppConfig:
    if not _CONFIG_PATH.exists():
        return AppConfig()
    with _CONFIG_PATH.open() as f:
        raw: dict = yaml.safe_load(f) or {}
    resolved = _substitute_env_vars(raw)
    return AppConfig.model_validate(resolved)
