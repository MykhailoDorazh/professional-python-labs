"""Engine, session factory and the transaction boundary (unit of work)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from employee_db.models import Base

DATABASE_URL = os.getenv("EMPLOYEE_DATABASE_URL", "sqlite:///employees.db")


def make_engine(url: str = DATABASE_URL, echo: bool = False) -> Engine:
    """Create an engine; for SQLite turn on FOREIGN KEY enforcement."""
    engine = create_engine(url, echo=echo)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: sqlite3.Connection, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

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
