"""OCR pipeline: native PDF text extraction + image OCR + LLM vision fallback."""

from __future__ import annotations

import base64
import io
from typing import Literal

from app.config import get_config
from app.core.logging import logger


async def extract_text_from_pdf(
    file_bytes: bytes,
    ocr_backend: Literal["tesseract", "llm"] = "tesseract",
    language: str = "eng",
) -> list[dict]:
    """
    Extract text from every page of a PDF.

    Returns a list of dicts: {"page": int, "text": str, "method": "native" | "ocr"}.
    Pages with native selectable text are extracted directly; scanned pages are
    routed through the chosen OCR backend.
    """
    try:
        import fitz  # pymupdf
    except ImportError as exc:
        raise RuntimeError(
            "pymupdf is required for PDF processing. "
            "Install it with: uv add pymupdf"
        ) from exc

    pages: list[dict] = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    for page_num, page in enumerate(doc):
        native_text = page.get_text().strip()

        if len(native_text) > 50:
            pages.append({"page": page_num + 1, "text": native_text, "method": "native"})
        else:
            # Scanned page – render to image and OCR
            mat = fitz.Matrix(2.0, 2.0)  # 2× zoom improves OCR accuracy
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            ocr_text = await _ocr_image_bytes(img_bytes, backend=ocr_backend, language=language)
            pages.append({"page": page_num + 1, "text": ocr_text, "method": "ocr"})
            logger.debug(f"PDF page {page_num + 1}: no native text, used {ocr_backend} OCR")

    doc.close()
    return pages


async def extract_text_from_image(
    file_bytes: bytes,
    backend: Literal["tesseract", "llm"] = "tesseract",
    language: str = "eng",
) -> str:
    """Extract text from a standalone image file (PNG/JPG/TIFF/BMP)."""
    return await _ocr_image_bytes(file_bytes, backend=backend, language=language)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _ocr_image_bytes(
    img_bytes: bytes,
    backend: Literal["tesseract", "llm"],
    language: str,
) -> str:
    if backend == "llm":
        return await _llm_vision_ocr(img_bytes)
    return _tesseract_ocr(img_bytes, language=language)


def _tesseract_ocr(img_bytes: bytes, language: str = "eng") -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract and Pillow are required for Tesseract OCR. "
            "Install with: uv add pytesseract Pillow"
        ) from exc

    cfg = get_config().get("document", {}).get("ocr", {})
    tesseract_path = cfg.get("tesseract_cmd")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    image = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(image, lang=language)


async def _llm_vision_ocr(img_bytes: bytes) -> str:
    """Use an LLM with vision capability to extract text from an image."""
    cfg = get_config()
    ocr_cfg = cfg.get("document", {}).get("ocr", {})
    provider = ocr_cfg.get("llm_provider", "anthropic")
    prompt = (
        "Extract all text from this image exactly as it appears. "
        "Return only the extracted text with no commentary, preamble, or markdown."
    )
    b64 = base64.standard_b64encode(img_bytes).decode()

    if provider == "anthropic":
        import anthropic
        llm_cfg = cfg["llm"]["providers"]["anthropic"]
        client = anthropic.AsyncAnthropic(api_key=llm_cfg["api_key"])
        msg = await client.messages.create(
            model=llm_cfg.get("default_model", "claude-sonnet-4-6"),
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return msg.content[0].text

    if provider == "openai":
        from openai import AsyncOpenAI
        llm_cfg = cfg["llm"]["providers"]["openai"]
        client = AsyncOpenAI(api_key=llm_cfg["api_key"])
        resp = await client.chat.completions.create(
            model=llm_cfg.get("default_model", "gpt-4o"),
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return resp.choices[0].message.content or ""

    raise ValueError(f"Unsupported OCR LLM provider: {provider!r}. Use 'anthropic' or 'openai'.")
