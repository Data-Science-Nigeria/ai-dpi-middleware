"""Document ingestion pipeline: extract → chunk → embed → store."""

from __future__ import annotations

from typing import Literal

from app.config import get_config
from app.core.logging import logger
from app.services.document.chunker import chunk_text
from app.services.document.extractors import extract as extract_office
from app.services.document.ocr import extract_text_from_image, extract_text_from_pdf
from app.services.embedding import main as embedding_service
from app.services.vectordb import main as vectordb


async def ingest_pdf(
    file_bytes: bytes,
    filename: str,
    collection_name: str | None = None,
    ocr_backend: Literal["tesseract", "llm"] = "tesseract",
    language: str = "eng",
) -> dict:
    """
    Full RAG ingestion for a PDF file.

    Extracts text page-by-page (native or OCR), chunks each page,
    embeds each chunk, and stores all vectors in the configured vector DB.

    Returns {"chunks_stored": int, "pages": int}.
    """
    collection_name = _collection(collection_name)

    pages = await extract_text_from_pdf(
        file_bytes, ocr_backend=ocr_backend, language=language
    )

    chunks, meta = _build_chunks(pages, filename)

    if not chunks:
        logger.warning(f"No extractable text found in {filename!r}")
        return {"chunks_stored": 0, "pages": len(pages)}

    embeddings = await _embed_all(chunks)
    await vectordb.add(
        collection_name=collection_name,
        embeddings=embeddings,
        documents=chunks,
        meta_data=meta,
    )

    logger.info(
        f"Ingested PDF {filename!r}: {len(pages)} pages → {len(chunks)} chunks "
        f"→ collection {collection_name!r}"
    )
    return {"chunks_stored": len(chunks), "pages": len(pages)}


async def ingest_image(
    file_bytes: bytes,
    filename: str,
    collection_name: str | None = None,
    ocr_backend: Literal["tesseract", "llm"] = "tesseract",
    language: str = "eng",
) -> dict:
    """Full RAG ingestion for a standalone image (PNG/JPG/TIFF/BMP)."""
    collection_name = _collection(collection_name)

    text = await extract_text_from_image(
        file_bytes, backend=ocr_backend, language=language
    )
    if not text.strip():
        logger.warning(f"No text extracted from image {filename!r}")
        return {"chunks_stored": 0, "pages": 1}

    chunks = chunk_text(text)
    meta = [{"source": filename, "page": 1, "chunk": i, "method": "ocr"} for i in range(len(chunks))]

    embeddings = await _embed_all(chunks)
    await vectordb.add(
        collection_name=collection_name,
        embeddings=embeddings,
        documents=chunks,
        meta_data=meta,
    )

    logger.info(f"Ingested image {filename!r}: {len(chunks)} chunks → collection {collection_name!r}")
    return {"chunks_stored": len(chunks), "pages": 1}


async def ingest_office(
    file_bytes: bytes,
    filename: str,
    collection_name: str | None = None,
) -> dict:
    """
    Full RAG ingestion for office / structured formats:
    DOCX, PPTX, XLSX, CSV, RTF, ODT, TXT, MD.

    Returns {"chunks_stored": int, "pages": int}.
    """
    collection_name = _collection(collection_name)

    pages = extract_office(file_bytes, filename)
    chunks, meta = _build_chunks(pages, filename)

    if not chunks:
        logger.warning(f"No extractable text found in {filename!r}")
        return {"chunks_stored": 0, "pages": len(pages)}

    embeddings = await _embed_all(chunks)
    await vectordb.add(
        collection_name=collection_name,
        embeddings=embeddings,
        documents=chunks,
        meta_data=meta,
    )

    logger.info(
        f"Ingested {filename!r}: {len(pages)} section(s) → {len(chunks)} chunks "
        f"→ collection {collection_name!r}"
    )
    return {"chunks_stored": len(chunks), "pages": len(pages)}


async def ingest_text(
    text: str,
    source: str = "text",
    collection_name: str | None = None,
) -> dict:
    """Full RAG ingestion for raw plain text."""
    collection_name = _collection(collection_name)

    chunks = chunk_text(text)
    if not chunks:
        return {"chunks_stored": 0, "pages": 1}

    meta = [{"source": source, "chunk": i} for i in range(len(chunks))]
    embeddings = await _embed_all(chunks)
    await vectordb.add(
        collection_name=collection_name,
        embeddings=embeddings,
        documents=chunks,
        meta_data=meta,
    )

    logger.info(f"Ingested text from {source!r}: {len(chunks)} chunks → collection {collection_name!r}")
    return {"chunks_stored": len(chunks), "pages": 1}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collection(name: str | None) -> str:
    return name or get_config()["llm"]["vector_database"]["collection_name"]


def _build_chunks(pages: list[dict], filename: str) -> tuple[list[str], list[dict]]:
    """Chunk every page and build matching metadata list."""
    all_chunks: list[str] = []
    all_meta: list[dict] = []

    for page_data in pages:
        if not page_data["text"].strip():
            continue
        page_chunks = chunk_text(page_data["text"])
        for i, chunk in enumerate(page_chunks):
            all_chunks.append(chunk)
            all_meta.append({
                "source": filename,
                "page": page_data["page"],
                "chunk": i,
                "method": page_data["method"],
            })

    return all_chunks, all_meta


async def _embed_all(chunks: list[str]) -> list[list[float]]:
    """Embed each chunk sequentially (respects rate limits on embedding API)."""
    embeddings: list[list[float]] = []
    for chunk in chunks:
        emb = await embedding_service.get_embedding(text=chunk)
        embeddings.append(emb)
    return embeddings
