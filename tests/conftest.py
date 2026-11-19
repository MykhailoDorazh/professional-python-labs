"""Fixtures: every test gets its own SQLite file in tmp_path (separate test DB)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from bank_account_service.database import init_db, make_engine, make_session_factory
from bank_account_service.services import BankService


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_bank.db"


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    engine = make_engine(f"sqlite:///{db_path}")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with make_session_factory(engine)() as session:
        yield session


@pytest.fixture
def bank(session: Session) -> BankService:
    return BankService(session)


@pytest.fixture
def seeded(bank: BankService) -> BankService:
    """Two clients, three accounts: UA1 = 1000.00, UA2 = 500.00, UA3 = 0.00."""
    anna = bank.register_client("Анна Коваль", "anna@example.com")
    oleh = bank.register_client("Олег Мельник")
    bank.open_account(anna.id, "UA1", "1000")
    bank.open_account(anna.id, "UA2", "500", "savings")
    bank.open_account(oleh.id, "UA3")
    return bank
