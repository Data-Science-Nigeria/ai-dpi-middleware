"""Document ingestion endpoints – all popular knowledge formats to RAG vector store."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.rbac import require_roles
from app.config import get_config
from app.schemas.document import IngestResponse
from app.services.document import pipeline
from app.services.document.extractors import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["Documents"])

# ── File type classification ──────────────────────────────────────────────────

_PDF_EXT = {".pdf"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
_OFFICE_EXT = SUPPORTED_EXTENSIONS  # .docx .pptx .xlsx .csv .rtf .odt .txt .md etc.

_PDF_MIME = {"application/pdf"}
_IMAGE_MIME = {"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/gif", "image/webp"}
_OFFICE_MIME = {
    # Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    # PowerPoint
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    # Text
    "text/plain", "text/markdown", "text/csv",
    # Open Document
    "application/vnd.oasis.opendocument.text",
    # RTF
    "application/rtf", "text/rtf",
}

_ALL_ACCEPTED = (
    sorted(_PDF_EXT) + sorted(_IMAGE_EXT) + sorted(_OFFICE_EXT)
)

_DEFAULT_MAX_MB = 50


def _classify(filename: str, content_type: str) -> Literal["pdf", "image", "office"] | None:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext in _PDF_EXT or content_type in _PDF_MIME:
        return "pdf"
    if ext in _IMAGE_EXT or content_type in _IMAGE_MIME:
        return "image"
    if ext in _OFFICE_EXT or content_type in _OFFICE_MIME:
        return "office"
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    summary="Ingest a document into the RAG vector store",
    description="""
Upload any popular knowledge format for RAG ingestion.

**Supported formats**:
- **PDF** – native text extraction; scanned pages fall back to OCR
- **Word** – `.docx`, `.doc`
- **PowerPoint** – `.pptx`, `.ppt` (includes slide notes)
- **Excel / Spreadsheet** – `.xlsx`, `.xls`, `.csv`
- **Open Document** – `.odt`
- **Rich Text** – `.rtf`
- **Plain text / Markdown** – `.txt`, `.md`
- **Images** – `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.gif`, `.webp`

**Pipeline**: extract text → sentence-aware chunking → embed → store in vector DB.

**`ocr_backend`** (PDF scanned pages and images only):
- `tesseract` *(default)* – fully local, requires Tesseract on the host.
- `llm` – Claude or GPT-4o vision; higher quality, requires API key.

Requires **admin** role.
""",
)
async def ingest_document(
    file: Annotated[UploadFile, File(description="Document file to ingest")],
    _user: Annotated[dict, Depends(require_roles("admin"))],
    collection_name: Annotated[str | None, Form(description="Target collection (uses default if omitted)")] = None,
    ocr_backend: Annotated[
        Literal["tesseract", "llm"],
        Form(description="OCR backend – applies to scanned PDFs and image files only"),
    ] = "tesseract",
    language: Annotated[str, Form(description="Tesseract language code, e.g. 'eng', 'fra', 'yor', 'swa'")] = "eng",
) -> IngestResponse:
    cfg = get_config().get("document", {})
    max_bytes = cfg.get("max_file_size_mb", _DEFAULT_MAX_MB) * 1024 * 1024

    content = await file.read()

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {cfg.get('max_file_size_mb', _DEFAULT_MAX_MB)} MB limit.",
        )

    filename = file.filename or "upload"
    ftype = _classify(filename, file.content_type or "")

    if ftype == "pdf":
        result = await pipeline.ingest_pdf(
            file_bytes=content,
            filename=filename,
            collection_name=collection_name,
            ocr_backend=ocr_backend,
            language=language,
        )
    elif ftype == "image":
        result = await pipeline.ingest_image(
            file_bytes=content,
            filename=filename,
            collection_name=collection_name,
            ocr_backend=ocr_backend,
            language=language,
        )
    elif ftype == "office":
        result = await pipeline.ingest_office(
            file_bytes=content,
            filename=filename,
            collection_name=collection_name,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type or 'unknown'}'. "
                f"Accepted extensions: {', '.join(_ALL_ACCEPTED)}."
            ),
        )

    return IngestResponse(
        filename=filename,
        collection_name=collection_name,
        **result,
    )


@router.post(
    "/ingest/text",
    summary="Ingest raw text into the RAG vector store",
    description="Directly ingest a text string without uploading a file. Useful for programmatic ingestion.",
)
async def ingest_raw_text(
    text: Annotated[str, Form(description="Plain text to ingest")],
    _user: Annotated[dict, Depends(require_roles("admin"))],
    source: Annotated[str, Form(description="Label for the source (used in metadata)")] = "manual",
    collection_name: Annotated[str | None, Form()] = None,
) -> IngestResponse:
    result = await pipeline.ingest_text(
        text=text,
        source=source,
        collection_name=collection_name,
    )
    return IngestResponse(filename=source, collection_name=collection_name, **result)
