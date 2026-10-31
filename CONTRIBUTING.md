# Contributing

Build changes on short-lived feature branches and open a pull request for review.

## Source structure

- `app/main.py` — FastAPI application wiring and health/dashboard routes
- `app/api/routes/` — HTTP endpoints and input validation
- `app/schemas/` — Pydantic request/response contracts
- `app/models/` — SQLAlchemy table definitions
- `app/db/` — engine, base and dependency-injected sessions
- `app/services/` — parsing, persistence and exporting
- `app/core/` — environment-based settings
- `tests/` — integration/API tests using isolated SQLite
- `scripts/` — one-off migration utilities

## Local checks

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Always add or extend tests for backend changes, and avoid committing databases, uploaded documents, credentials or personal data. **Do not deploy the current unauthenticated API publicly.**
