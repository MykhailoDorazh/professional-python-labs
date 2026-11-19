"""Engine, session factory and the transaction boundary (unit of work)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from employee_api.models import Base

DATABASE_URL = os.getenv("EMPLOYEE_DATABASE_URL", "sqlite:///employees.db")


def unicode_lower(value: str | None) -> str | None:
    """SQLite's built-in lower() changes only ASCII letters ('Розробник' stays as is)."""
    return value.lower() if value is not None else None


def make_engine(url: str = DATABASE_URL, echo: bool = False) -> Engine:
    """Create an engine; for SQLite turn on FOREIGN KEY enforcement and replace
    lower() (used by ILIKE) with a Unicode-aware version for Cyrillic search."""
    engine = create_engine(url, echo=echo)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection: sqlite3.Connection, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
            dbapi_connection.create_function("lower", 1, unicode_lower, deterministic=True)

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create all tables (used by the demo and tests; real DB uses Alembic)."""
    Base.metadata.create_all(engine)


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    """Unit of work: COMMIT if the block succeeds, ROLLBACK on any exception."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
