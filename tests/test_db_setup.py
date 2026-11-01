"""The database connectivity diagnostic must work in CI without PostgreSQL."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_database_check_with_isolated_sqlite(tmp_path):
    db = tmp_path / "test.sqlite3"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db}"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_db"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sqlite connection OK" in result.stdout
    assert db.exists()
