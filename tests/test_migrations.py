"""Alembic migrations on a separate test database: upgrade, downgrade, no drift."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from bank_account_service.migrate import alembic_config, upgrade


@pytest.fixture
def alembic_cfg(tmp_path: Path) -> Config:
    """Migrations shipped inside the package (as in the Docker image)."""
    return alembic_config(f"sqlite:///{tmp_path / 'migrated.db'}")


def columns(db: Path, table: str) -> list[str]:
    # sqlite3 connection as a context manager only commits; closing() really closes it
    with closing(sqlite3.connect(db)) as connection:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def test_upgrade_head_creates_schema(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "head")
    db = tmp_path / "migrated.db"
    assert "account_type" in columns(db, "accounts")
    assert columns(db, "transactions")[:3] == ["id", "account_id", "kind"]


def test_downgrade_removes_account_type(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "0001")
    assert "account_type" not in columns(tmp_path / "migrated.db", "accounts")
    command.downgrade(alembic_cfg, "base")
    assert columns(tmp_path / "migrated.db", "accounts") == []


def test_existing_rows_get_default_type(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "0001")
    db = tmp_path / "migrated.db"
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute("INSERT INTO clients (full_name) VALUES ('Анна')")
        connection.execute(
            "INSERT INTO accounts (number, balance_cents, client_id) VALUES ('UA1', 100, 1)"
        )
    command.upgrade(alembic_cfg, "head")
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute("SELECT account_type FROM accounts").fetchone() == ("current",)


def test_models_match_migrations(alembic_cfg: Config) -> None:
    """`alembic check`: the ORM models have no changes missing from migrations."""
    command.upgrade(alembic_cfg, "head")
    command.check(alembic_cfg)


def test_single_head(alembic_cfg: Config) -> None:
    assert ScriptDirectory.from_config(alembic_cfg).get_heads() == ["0002"]


def test_upgrade_helper_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'twice.db'}"
    upgrade(url)
    upgrade(url)  # second run: nothing to do, no error
    assert "account_type" in columns(tmp_path / "twice.db", "accounts")
