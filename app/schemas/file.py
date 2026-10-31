"""API response schemas; binary file data is intentionally excluded."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FileMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    kind: str
    mime_type: str | None
    file_size_bytes: int
    sha256: str
    status: str
    rows_count: int | None
    created_at: datetime


class UploadResult(BaseModel):
    id: str
    filename: str
    status: str
    rows_count: int | None


class DatasetData(BaseModel):
    id: str
    total: int
    limit: int
    offset: int
    records: list[dict[str, Any]]


class PdfData(BaseModel):
    id: str
    text: str
    page_count: int
