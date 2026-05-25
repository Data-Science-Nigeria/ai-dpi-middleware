"""Text chunker: splits documents into overlapping sentence-aware chunks."""

from __future__ import annotations

import re

from app.config import get_config


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap_sentences: int | None = None,
    min_length: int | None = None,
) -> list[str]:
    """
    Split *text* into overlapping chunks suitable for embedding.

    Strategy:
    1. Split into sentences on sentence-ending punctuation.
    2. Accumulate sentences until the chunk exceeds *chunk_size* characters.
    3. On overflow, emit the current chunk and seed the next one with the last
       *overlap_sentences* sentences so context isn't lost at boundaries.
    4. Discard sentences shorter than *min_length* (noise / headers).

    Returns a list of non-empty chunk strings.
    """
    cfg = get_config().get("document", {})
    overlap_sentences = overlap_sentences if overlap_sentences is not None else cfg.get("chunk_overlap_sentences", 3)
    min_length = min_length if min_length is not None else cfg.get("min_paragraph_length", 50)

    sentences = _split_sentences(text)
    sentences = [s for s in sentences if len(s) >= min_length]

    if not sentences:
        stripped = text.strip()
        return [stripped] if stripped else []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > chunk_size and current:
            chunks.append(" ".join(current))
            # Seed next chunk with tail overlap for continuity
            overlap = current[-overlap_sentences:] if overlap_sentences > 0 else []
            current = list(overlap)
            current_len = sum(len(s) for s in current)

        current.append(sentence)
        current_len += len(sentence)

    if current:
        chunks.append(" ".join(current))

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Normalise whitespace then split on sentence-ending punctuation."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]
