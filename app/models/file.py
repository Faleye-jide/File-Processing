"""Relational persistence for uploaded binaries, tabular rows and PDF text."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    rows_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # MVP decision: persist the original file in the DB. Use object storage for larger scale.
    original_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rows: Mapped[list["DatasetRecord"]] = relationship(back_populates="file", cascade="all, delete-orphan")
    document: Mapped["DocumentContent | None"] = relationship(back_populates="file", cascade="all, delete-orphan", uselist=False)


class DatasetRecord(Base):
    __tablename__ = "dataset_records"
    __table_args__ = (
        UniqueConstraint("file_id", "row_number", name="uq_dataset_record_position"),
        Index("ix_dataset_records_file_id", "file_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    file: Mapped[UploadedFile] = relationship(back_populates="rows")


class DocumentContent(Base):
    __tablename__ = "document_contents"

    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id", ondelete="CASCADE"), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)

    file: Mapped[UploadedFile] = relationship(back_populates="document")
