"""SQLAlchemy models for the Todo API."""

from sqlalchemy import Boolean, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class Todo(Base):
    """Todo item database model."""

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_todos_title_ci", func.lower(title), unique=True),
        {"sqlite_autoincrement": True},
    )
