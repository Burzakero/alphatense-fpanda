"""SQLAlchemy ORM tables. See app/db/database.py for engine/session setup."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utcnow() -> datetime:
    # Naive UTC, deliberately -- SQLite's DATETIME column doesn't preserve
    # tzinfo on round-trip (SQLAlchemy reads it back naive regardless of
    # DateTime(timezone=True)), so every datetime in this app is naive UTC
    # by convention to keep comparisons consistent. Never mix in an
    # aware datetime here.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AdvisorAccount(Base):
    __tablename__ = "advisors"

    advisor_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    advisor_id: Mapped[str] = mapped_column(ForeignKey("advisors.advisor_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    workspace_id: Mapped[str] = mapped_column(String, primary_key=True)
    advisor_id: Mapped[str] = mapped_column(ForeignKey("advisors.advisor_id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
