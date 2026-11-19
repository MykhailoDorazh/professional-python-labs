"""Alembic migrations on a separate test database: upgrade, downgrade, no drift."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("EMPLOYEE_DATABASE_URL", f"sqlite:///{tmp_path / 'migrated.db'}")
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


def columns(db: Path, table: str) -> list[str]:
    # sqlite3 connection as a context manager only commits; closing() really closes it
    with closing(sqlite3.connect(db)) as connection:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def test_upgrade_head_creates_schema(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "head")
    db = tmp_path / "migrated.db"
    assert columns(db, "departments") == ["id", "code", "name"]
    assert "hire_date" in columns(db, "employees")


def test_downgrade_removes_hire_date(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "0001")
    assert "hire_date" not in columns(tmp_path / "migrated.db", "employees")
    command.downgrade(alembic_cfg, "base")
    assert columns(tmp_path / "migrated.db", "employees") == []


def test_existing_rows_survive_migration(alembic_cfg: Config, tmp_path: Path) -> None:
    command.upgrade(alembic_cfg, "0001")
    db = tmp_path / "migrated.db"
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute("INSERT INTO departments (code, name) VALUES ('IT', 'ІТ')")
        connection.execute("INSERT INTO employees (personnel_number, full_name, position, "
                           "salary_cents, department_id) VALUES ('E0001', 'Олена', 'Тімлід', "
                           "9000000, 1)")
    command.upgrade(alembic_cfg, "head")
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute(
            "SELECT personnel_number, salary_cents, hire_date FROM employees").fetchone() == (
            "E0001", 9_000_000, None)


def test_models_match_migrations(alembic_cfg: Config) -> None:
    """`alembic check`: the ORM models have no changes missing from migrations."""
    command.upgrade(alembic_cfg, "head")
    command.check(alembic_cfg)


def test_single_head() -> None:
    script = ScriptDirectory(str(ROOT / "migrations"))
    assert script.get_heads() == ["0002"]
