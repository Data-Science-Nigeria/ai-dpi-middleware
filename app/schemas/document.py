from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    filename: str
    chunks_stored: int
    pages: int = Field(default=1)
    collection_name: str | None = None
