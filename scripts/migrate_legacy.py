"""Optionally import old file-based Sprint 1 uploads into the new database.

Usage: python -m scripts.migrate_legacy

Existing files and the old SQLite database are never deleted. Existing file IDs
are preserved; rerunning this script skips files already imported.
"""

import sqlite3
import uuid
from pathlib import Path

from app.core.config import ALLOWED_EXTENSIONS, PROJECT_ROOT
from app.db.session import SessionLocal, create_db_and_tables
from app.services.file_processing import FileProcessingError, parse_file
from app.services.file_service import get_upload, persist_upload


def migrate(storage: Path | None = None) -> tuple[int, int]:
    storage = storage or PROJECT_ROOT / "storage"
    old_db = storage / "metadata.sqlite3"
    if not old_db.exists():
        print(f"No legacy database found at {old_db}")
        return 0, 0

    create_db_and_tables()
    copied = 0
    skipped = 0
    with sqlite3.connect(old_db) as conn, SessionLocal() as db:
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT id, filename, kind FROM files"):
            try:
                file_id = str(uuid.UUID(row["id"]))
                extension = "." + row["kind"].lower()
                if extension not in ALLOWED_EXTENSIONS or get_upload(db, file_id) is not None:
                    skipped += 1
                    continue
                file_path = storage / f"{file_id}{extension}"
                content = file_path.read_bytes()
                processed = parse_file(content, extension)
                persist_upload(
                    db, file_id=file_id, filename=row["filename"],
                    extension=extension, mime_type=None, content=content, processed=processed,
                )
                copied += 1
            except (FileNotFoundError, ValueError, FileProcessingError) as exc:
                print(f"Skipping legacy file {row['id']}: {exc}")
                skipped += 1
    print(f"Imported: {copied}; skipped: {skipped}")
    return copied, skipped


if __name__ == "__main__":
    migrate()
