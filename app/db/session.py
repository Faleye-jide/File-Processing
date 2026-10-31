"""SQLAlchemy engine and request-scoped database sessions."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
from app.db.base import Base

# The default SQLite database lives under storage/, which is ignored by Git.
if DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:
    Path(DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

# sqlite connect_args are required when FastAPI serves a request on another thread.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def create_db_and_tables() -> None:
    # Import model declarations before calling create_all (MVP only).
    import app.models.file  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
