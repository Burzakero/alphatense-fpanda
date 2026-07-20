"""
SQLite persistence, deliberately minimal.

DATABASE_PATH controls where the file lives -- defaults to a local `data/`
folder (gitignored) for development, and points at a Railway persistent
volume mount in production so advisor accounts and workspace data survive
redeploys/restarts. No Alembic: the schema is small and pre-launch, so
`Base.metadata.create_all()` on startup is enough.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_path() -> Path:
    raw = os.getenv("DATABASE_PATH", "./data/alphatense.db")
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


_engine = create_engine(f"sqlite:///{_database_path()}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def init_db() -> None:
    from app.db import models  # noqa: F401  (registers tables on Base.metadata)

    Base.metadata.create_all(bind=_engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
