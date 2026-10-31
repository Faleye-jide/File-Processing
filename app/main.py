from __future__ import annotations

import io
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

import pymupdf
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

ROOT = Path(os.getenv("DATAFLOW_STORAGE", Path(__file__).resolve().parent.parent / "storage"))
ROOT.mkdir(parents=True, exist_ok=True)
DB = ROOT / "metadata.sqlite3"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {".csv", ".xlsx", ".json", ".pdf"}


@contextmanager
def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


with connect() as con:
    con.execute("""CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY, filename TEXT NOT NULL, kind TEXT NOT NULL,
        rows_count INTEGER, status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

app = FastAPI(title="File Processing API", version="0.1.0")


def get_file(file_id: str) -> dict:
    with connect() as con:
        row = con.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "File not found")
    return dict(row)


def parse(content: bytes, extension: str):
    if extension == ".csv":
        df = pd.read_csv(io.BytesIO(content))
    elif extension == ".xlsx":
        df = pd.read_excel(io.BytesIO(content))
    elif extension == ".json":
        payload = json.loads(content)
        if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
            raise ValueError("JSON input must be an array of objects")
        df = pd.DataFrame(payload)
    else:
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
        if not text.strip():
            raise ValueError("No embedded text found; scanned PDFs require OCR (Sprint 2)")
        return {"text": text}, None
    df = df.where(pd.notna(df), None)
    # JSON roundtrip normalizes pandas / numpy scalar and timestamp types.
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    return {"records": records}, len(records)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/files/upload", status_code=201)
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, "Supported extensions: CSV, XLSX, JSON, PDF")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Maximum file size is 10 MB")
    try:
        parsed, count = parse(content, ext)
    except Exception as exc:
        # Parsing failures should never expose server internals.
        raise HTTPException(422, f"Unable to process file: {type(exc).__name__}") from exc
    file_id = str(uuid.uuid4())
    (ROOT / f"{file_id}{ext}").write_bytes(content)
    (ROOT / f"{file_id}.processed.json").write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    with connect() as con:
        con.execute(
            "INSERT INTO files (id, filename, kind, rows_count, status) VALUES (?, ?, ?, ?, ?)",
            (file_id, name, ext[1:], count, "completed"),
        )
    return {"id": file_id, "filename": name, "status": "completed", "rows_count": count}


@app.get("/api/v1/files")
def list_files():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM files ORDER BY created_at DESC")]


@app.get("/api/v1/files/{file_id}")
def file_metadata(file_id: str):
    return get_file(file_id)


@app.get("/api/v1/files/{file_id}/data")
def file_data(file_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    metadata = get_file(file_id)
    payload = json.loads((ROOT / f"{file_id}.processed.json").read_text(encoding="utf-8"))
    if metadata["kind"] == "pdf":
        return {"id": file_id, **payload}
    records = payload["records"]
    return {
        "id": file_id, "total": len(records), "limit": limit, "offset": offset,
        "records": records[offset:offset + limit],
    }


@app.get("/api/v1/files/{file_id}/download")
def download(file_id: str, format: str = Query("json", pattern="^(csv|json)$")):
    metadata = get_file(file_id)
    payload = json.loads((ROOT / f"{file_id}.processed.json").read_text(encoding="utf-8"))
    if format == "csv":
        if metadata["kind"] == "pdf":
            raise HTTPException(422, "PDF text cannot be exported as tabular CSV in Sprint 1")
        content = pd.DataFrame(payload["records"]).to_csv(index=False).encode("utf-8")
        media_type = "text/csv"
    else:
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        media_type = "application/json"
    return Response(
        content=content, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_id}.{format}"'},
    )


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "index.html")
