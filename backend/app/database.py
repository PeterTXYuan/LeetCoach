"""Shared database configuration for the API, Alembic, and seed command."""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Base(DeclarativeBase):
    pass


def get_database_url():
    configured = os.environ.get("LEETCOACH_DATABASE_URL")
    url = make_url(configured) if configured else URL.create(
        "sqlite", database=str(BACKEND_DIR / "leetcoach.db")
    )
    # Relative SQLite paths always resolve from backend/, regardless of cwd.
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        path = Path(url.database)
        if not path.is_absolute():
            url = url.set(database=str((BACKEND_DIR / path).resolve()))
    return url


def create_database_engine(url=None):
    url = make_url(url) if url is not None else get_database_url()
    options = {"connect_args": {"check_same_thread": False}} if url.get_backend_name() == "sqlite" else {}
    engine = create_engine(url, **options)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine)


def get_session():
    with SessionLocal() as session:
        yield session
