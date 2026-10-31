"""Application composition. Routes, models and persistence live in dedicated modules."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes.files import router as files_router
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="File Processing API", version="0.2.0", lifespan=lifespan)
app.include_router(files_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "index.html")
