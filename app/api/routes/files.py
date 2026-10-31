"""File endpoints. Routes delegate parsing and persistence to services."""

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from app.db.session import get_db
from app.models.file import DocumentContent
from app.schemas.file import DatasetData, FileMetadata, PdfData, UploadResult
from app.services.file_processing import FileProcessingError, parse_file
from app.services.file_service import export_file, get_upload, list_rows, list_uploads, persist_upload

router = APIRouter(prefix="/api/v1/files", tags=["Files"])


def require_upload(db: Session, file_id: str):
    uploaded = get_upload(db, file_id)
    if uploaded is None:
        raise HTTPException(status_code=404, detail="File not found")
    return uploaded


@router.post("/upload", status_code=201, response_model=UploadResult)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Strip path components from files supplied by a client on any OS.
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename or len(filename) > 255 or any(ord(c) < 32 for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Supported extensions: CSV, XLSX, JSON, PDF")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 10 MB")
    try:
        processed = parse_file(content, extension)
    except FileProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = persist_upload(db, filename=filename, extension=extension, mime_type=file.content_type, content=content, processed=processed)
    return UploadResult(id=result.id, filename=result.filename, status=result.status, rows_count=result.rows_count)


@router.get("", response_model=list[FileMetadata])
def list_files(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return list_uploads(db, limit=limit, offset=offset)


@router.get("/{file_id}", response_model=FileMetadata)
def file_metadata(file_id: str, db: Session = Depends(get_db)):
    return require_upload(db, file_id)


@router.get("/{file_id}/data", response_model=DatasetData | PdfData)
def file_data(file_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    uploaded = require_upload(db, file_id)
    if uploaded.kind == "pdf":
        content = db.get(DocumentContent, file_id)
        if content is None:
            raise HTTPException(status_code=500, detail="Document content missing")
        return PdfData(id=file_id, text=content.text, page_count=content.page_count)
    return DatasetData(id=file_id, total=uploaded.rows_count or 0, limit=limit, offset=offset, records=list_rows(db, file_id, limit=limit, offset=offset))


@router.get("/{file_id}/download")
def download(file_id: str, format: str = Query("json", pattern="^(csv|json)$"), db: Session = Depends(get_db)):
    uploaded = require_upload(db, file_id)
    try:
        content, media_type = export_file(db, uploaded, format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={file_id}.{format}"})


@router.get("/{file_id}/original")
def download_original(file_id: str, db: Session = Depends(get_db)):
    uploaded = require_upload(db, file_id)
    filename = quote(uploaded.filename, safe="")
    return Response(
        content=uploaded.original_content,
        media_type=uploaded.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
