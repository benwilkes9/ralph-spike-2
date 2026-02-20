"""SQLAlchemy models."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ralf_spike_2.database import Base


class Todo(Base):
    """Todo item model."""

    __tablename__ = "todos"
    __table_args__ = {"sqlite_autoincrement": True}  # noqa: RUF012  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(
        String(500, collation="NOCASE"), nullable=False, unique=True
    )
    completed: Mapped[bool] = mapped_column(default=False)
