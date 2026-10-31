# Contributing

Work from a feature branch, add tests for backend changes and keep pull requests focused.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ for the dashboard, and http://127.0.0.1:8000/docs for API docs.

Avoid committing customer documents or other sensitive data. The current API is suitable for local testing only.
