# File Processing

An extensible FastAPI application for uploading CSV, Excel, JSON and text-based PDFs, persisting their contents in a database, and serving data via REST APIs. Includes a browser dashboard for uploads, previews and downloads.

## Architecture

```text
Browser dashboard (frontend/index.html + JS/CSS assets)
        |
        v
FastAPI (app/main.py) — application wiring only
        |
        v
API routes (app/api/routes/files.py)
        |
        +----> Processing service (app/services/file_processing.py)
        |          CSV / Excel / JSON -> JSON records
        |          PDF -> extracted text + page count
        |
        v
Persistence service (app/services/file_service.py)
        |
        v
SQLAlchemy ORM (app/models/file.py)
        |
        v
SQLite (default) or PostgreSQL (DATABASE_URL)
```

The database has three tables:

- **`uploaded_files`**: upload metadata, SHA-256, size and original file bytes (`LargeBinary` / PostgreSQL `BYTEA`).
- **`dataset_records`**: one JSON row per tabular input record, linked to its uploaded file.
- **`document_contents`**: extracted text and page count for text-based PDFs.

This means **the original upload AND the processed data live in the database**, not separate JSON files. Files can be queried, exported and downloaded after server restarts. A single transaction saves each upload and all its parsed records.

> **MVP trade-off:** Keeping a copy of every original binary in the database is workable under the current 10 MB limit. For larger production files, move original bytes to object storage (Azure Blob / S3), keeping object keys, metadata, structured rows and extracted text in PostgreSQL. For large structured datasets, consider bulk loading to dedicated tables or Parquet.

## Frontend structure

The frontend is currently a lightweight, framework-free browser app served by FastAPI:

```text
frontend/
├── index.html         # Page markup
├── js/
│   └── app.js         # Upload, list, preview, download and API calls
└── css/
    └── styles.css     # Dashboard styling
```

FastAPI mounts `frontend/` at `/static`, so `index.html` loads `/static/js/app.js` and `/static/css/styles.css`. This keeps HTML free of inline scripts and styles. No separate frontend build command is needed.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`

- **Dashboard:** http://127.0.0.1:8000/
- **Swagger docs:** http://127.0.0.1:8000/docs
- **Health:** http://127.0.0.1:8000/health

By default the database is `storage/file_processing.sqlite3` (automatically created). Data in `storage/` is ignored by Git.

### PostgreSQL on macOS (pgAdmin or Postgres.app)

Use the existing PostgreSQL server on your Mac. There is no need to install `psql` or run another server.

1. In pgAdmin confirm the database `file_processing` exists. Check the actual server port and username:

   ```sql
   SELECT version(), current_database(), current_user, inet_server_port();
   ```

2. Set up local config (never commit `.env`):

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and replace the placeholders, using the port shown by pgAdmin:

   ```dotenv
   DATABASE_URL=postgresql+psycopg://YOUR_DB_USER:YOUR_DB_PASSWORD@127.0.0.1:5432/file_processing
   ```

   URL-encode special characters in passwords. `DATABASE_URL` from the shell takes precedence over `.env`.

3. Validate the connection and run the API:

   ```bash
   pip install -r requirements.txt
   python -m scripts.check_db
   python -m uvicorn app.main:app --reload
   ```

4. Upload a test CSV through http://127.0.0.1:8000 and inspect the **file_processing** database in pgAdmin:

   ```sql
   SELECT filename, kind, rows_count FROM uploaded_files ORDER BY created_at DESC;
   SELECT file_id, row_number, data FROM dataset_records LIMIT 10;
   ```

The PostgreSQL database must already exist and the configured role must have permission to create tables. SQLAlchemy creates missing tables for this MVP, not production schema migrations. When `DATABASE_URL` is omitted, SQLite remains the default. Switching database URLs does **not** migrate old SQLite data automatically.

**Troubleshooting:** If the connection is refused, verify the server and port in Postgres.app; if authentication fails, verify the database role and password. The diagnostic deliberately avoids printing secrets.

## API

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/api/v1/files/upload` | Upload a CSV, XLSX, JSON or PDF (max 10 MB) |
| `GET` | `/api/v1/files?limit=100&offset=0` | List uploaded files with metadata |
| `GET` | `/api/v1/files/{id}` | Get metadata without binary content |
| `GET` | `/api/v1/files/{id}/data?limit=100&offset=0` | Query structured records, or PDF text |
| `GET` | `/api/v1/files/{id}/download?format=json` | Export processed data to JSON |
| `GET` | `/api/v1/files/{id}/download?format=csv` | Export tabular records to CSV |
| `GET` | `/api/v1/files/{id}/original` | Download the original file from the database |

Example:

```bash
curl -F 'file=@orders.csv' http://127.0.0.1:8000/api/v1/files/upload
curl http://127.0.0.1:8000/api/v1/files
```

## Upgrade from the old file-based app

The previous version stored metadata at `storage/metadata.sqlite3` and kept upload bytes and processed JSON files in `storage/`. **Those old files are left untouched**. To import them into the new schema:

```bash
python -m scripts.migrate_legacy
```

The importer preserves upload IDs where possible and skips IDs already imported. Back up `storage/` before migration. The new application uses a separate database at `storage/file_processing.sqlite3`, avoiding accidental overwrites of the old schema.

## Tests

```bash
python -m pytest -q
```

Tests create an isolated in-memory SQLite database, so test uploads never modify your application database. GitHub Actions runs these tests on PRs.

## Important limitations

- This is a **local development MVP**, not an authenticated production service. Never deploy it openly or upload real customer invoices, payment information, private information or secrets until authorization, encryption, scanning and retention controls are implemented.
- PDF handling extracts **embedded text only**; scanned documents require future OCR and AI extraction.
- Processing is synchronous; large workloads need a background queue.
- `create_all()` initializes tables but does **not** handle future schema changes; use Alembic migrations before evolving a deployed database.
- SQLite stores JSON as JSON-compatible values; PostgreSQL can provide richer JSON querying and indexing.

## Next milestones

1. Pydantic invoice, receipt and hotel bill schemas with deterministic field validation.
2. OCR and AI-based extraction with manual review.
3. Async processing (Redis/Celery), access controls, object storage and secure deployment.
