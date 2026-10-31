# File Processing

A local-first FastAPI web app for ingesting files and serving processed data through REST endpoints.

**Sprint 1:** upload CSV, XLSX, JSON and text-based PDFs, preview processed content, and export tabular records to CSV or JSON.

> **Security warning:** This is a local-development MVP with no authentication, malware scanning or encryption at rest. Do not deploy publicly or upload real invoices, private information, or credentials. OCR and AI-based field extraction are not yet implemented.

## Local setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

- Dashboard: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## API

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/v1/files/upload` | Upload up to 10 MB |
| GET | `/api/v1/files` | List files |
| GET | `/api/v1/files/{file_id}` | File metadata |
| GET | `/api/v1/files/{file_id}/data` | Paginated records or PDF text |
| GET | `/api/v1/files/{file_id}/download?format=json` | JSON export |
| GET | `/api/v1/files/{file_id}/download?format=csv` | CSV export (tabular only) |

```bash
curl -F 'file=@orders.csv' http://127.0.0.1:8000/api/v1/files/upload
pytest -q
```

## Cursor workflow

Clone the existing repository and open it in Cursor:

```bash
git clone https://github.com/Faleye-jide/File-Processing.git
cd File-Processing
git fetch origin
git switch feat/initial-file-processing-app
```

Review changes in the branch or the pull request before merging. The `.cursor/rules/project.mdc` file provides project-specific implementation rules.

## Roadmap

1. Add invoice, receipt and hotel bill schemas, and deterministic field validation.
2. Add OCR and AI-assisted extraction with human review.
3. Move processing to a background queue and store documents in object storage.
4. Implement authentication, file scanning, deployment and observability.

Current limitations: synchronous uploads, local SQLite/filesystem storage, text PDFs only; no PDF-to-tabular CSV conversion.