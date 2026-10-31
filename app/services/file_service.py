"""Database access and export operations for uploaded files."""

import csv
import hashlib
import io
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file import DatasetRecord, DocumentContent, UploadedFile
from app.services.file_processing import ProcessedFile


def persist_upload(
    db: Session,
    *,
    filename: str,
    extension: str,
    mime_type: str | None,
    content: bytes,
    processed: ProcessedFile,
    file_id: str | None = None,
) -> UploadedFile:
    """Persist original bytes and parsed contents in one database transaction."""
    record_rows = processed.rows
    uploaded = UploadedFile(
        id=file_id or str(uuid.uuid4()),
        filename=filename,
        kind=extension.lstrip("."),
        mime_type=mime_type,
        file_size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        status="completed",
        rows_count=len(record_rows) if record_rows is not None else None,
        original_content=content,
    )
    try:
        db.add(uploaded)
        if record_rows is not None:
            db.add_all(
                DatasetRecord(file_id=uploaded.id, row_number=index, data=row)
                for index, row in enumerate(record_rows)
            )
        if processed.text is not None:
            db.add(DocumentContent(file_id=uploaded.id, text=processed.text, page_count=processed.page_count or 0))
        db.commit()
        db.refresh(uploaded)
    except Exception:
        db.rollback()
        raise
    return uploaded


def list_uploads(db: Session, limit: int = 100, offset: int = 0) -> list[UploadedFile]:
    return list(db.scalars(select(UploadedFile).order_by(UploadedFile.created_at.desc(), UploadedFile.id.desc()).offset(offset).limit(limit)))


def get_upload(db: Session, file_id: str) -> UploadedFile | None:
    return db.get(UploadedFile, file_id)


def list_rows(db: Session, file_id: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
    statement = (
        select(DatasetRecord.data)
        .where(DatasetRecord.file_id == file_id)
        .order_by(DatasetRecord.row_number)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def all_rows(db: Session, file_id: str) -> list[dict[str, Any]]:
    return list_rows(db, file_id, limit=2**31 - 1, offset=0)


def export_file(db: Session, uploaded: UploadedFile, format: str) -> tuple[bytes, str]:
    if uploaded.kind == "pdf":
        if format == "csv":
            raise ValueError("PDF text cannot be exported as tabular CSV yet")
        content = db.get(DocumentContent, uploaded.id)
        payload = {"text": content.text, "page_count": content.page_count} if content else {"text": "", "page_count": 0}
    else:
        payload = {"records": all_rows(db, uploaded.id)}

    if format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json"

    rows = payload["records"]
    stream = io.StringIO()
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    if fieldnames:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return stream.getvalue().encode("utf-8"), "text/csv"
