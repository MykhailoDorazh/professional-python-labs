"""Fixtures: every test gets its own SQLite file in tmp_path (separate test DB)."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from employee_db.database import init_db, make_engine, make_session_factory
from employee_db.services import HRService


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_employees.db"


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
def hr(session: Session) -> HRService:
    return HRService(session)


@pytest.fixture
def seeded(hr: HRService) -> HRService:
    """IT: E0001 = 90 000, E0002 = 60 000; FIN: E0003 = 30 000.50; HR is empty."""
    hr.create_department("IT", "Інформаційні технології")
    hr.create_department("FIN", "Фінанси")
    hr.create_department("HR", "Персонал")
    hr.hire("E0001", "Олена Коваль", "Тімлід", "90000", "IT", date(2021, 3, 1))
    hr.hire("E0002", "Іван Петренко", "Розробник", "60000", "IT")
    hr.hire("E0003", "Андрій Мельник", "Бухгалтер", "30000.50", "FIN")
    return hr
