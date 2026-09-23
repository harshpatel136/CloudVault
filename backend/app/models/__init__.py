from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    files: Mapped[list["File"]] = relationship(
        back_populates="owner",
    )


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    object_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    file_size: Mapped[int] = mapped_column(
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    owner: Mapped[User] = relationship(
        back_populates="files",
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)

    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

    file: Mapped[File] = relationship(
        back_populates="chunks",
    )