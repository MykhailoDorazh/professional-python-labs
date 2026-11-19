"""Database migrations from the installed package (no alembic.ini needed)."""

from __future__ import annotations

from importlib.resources import files

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(files("bank_account_service") / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def upgrade(database_url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(database_url), revision)
