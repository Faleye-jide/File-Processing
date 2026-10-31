"""Input parsing is independent of HTTP and persistence."""

import io
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd
import pymupdf


class FileProcessingError(ValueError):
    """The uploaded bytes could not be interpreted in the expected format."""


@dataclass(frozen=True)
class ProcessedFile:
    rows: list[dict[str, Any]] | None = None
    text: str | None = None
    page_count: int | None = None


def parse_file(content: bytes, extension: str) -> ProcessedFile:
    try:
        if extension == ".pdf":
            with pymupdf.open(stream=content, filetype="pdf") as document:
                page_count = len(document)
                extracted = "\n".join(page.get_text() for page in document)
            if not extracted.strip():
                raise FileProcessingError("No embedded text found. Scanned PDFs require OCR (planned).")
            return ProcessedFile(text=extracted, page_count=page_count)

        if extension == ".csv":
            frame = pd.read_csv(io.BytesIO(content))
        elif extension == ".xlsx":
            frame = pd.read_excel(io.BytesIO(content))
        elif extension == ".json":
            payload = json.loads(content)
            if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
                raise FileProcessingError("JSON must contain an array of objects")
            frame = pd.DataFrame(payload)
        else:
            raise FileProcessingError("Unsupported file extension")

        # Convert pandas values (NaN, timestamps, numpy scalars) to JSON-safe types.
        rows = json.loads(frame.to_json(orient="records", date_format="iso"))
        return ProcessedFile(rows=rows)
    except FileProcessingError:
        raise
    except (ValueError, TypeError, UnicodeError, OSError, RuntimeError, KeyError) as exc:
        raise FileProcessingError("Unable to parse the supplied file") from exc
