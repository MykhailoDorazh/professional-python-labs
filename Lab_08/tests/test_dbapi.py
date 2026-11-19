"""Plain sqlite3 (DB-API) access to the same database file."""

import sqlite3
from pathlib import Path

import pytest

from employee_api.dbapi import find_by_department, raise_salary_raw, table_ddl
from employee_api.services import HRService


def test_find_by_department(seeded: HRService, db_path: Path) -> None:
    rows = find_by_department(db_path, "IT")
    assert [(r.personnel_number, r.salary_cents) for r in rows] == [
        ("E0001", 9_000_000), ("E0002", 6_000_000)]
    assert rows[0].full_name == "Олена Коваль" and rows[0].position == "Тімлід"


def test_empty_and_unknown_department(seeded: HRService, db_path: Path) -> None:
    assert find_by_department(db_path, "HR") == []
    assert find_by_department(db_path, "SALES") == []


def test_sql_injection_is_not_possible(seeded: HRService, db_path: Path) -> None:
    assert find_by_department(db_path, "' OR '1'='1") == []


def test_raw_mass_raise_commit(seeded: HRService, db_path: Path) -> None:
    assert raise_salary_raw(db_path, "IT", 10) == 2
    seeded.session.expire_all()
    assert seeded.get_employee("E0002").salary_cents == 6_600_000


def test_raw_mass_raise_rollback_on_check(seeded: HRService, db_path: Path) -> None:
    """+1100 %: E0002 -> 720 000 (valid), E0001 -> 1 080 000 (CHECK fails) -> nothing saved."""
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        raise_salary_raw(db_path, "IT", 1100)
    rows = {r.personnel_number: r.salary_cents for r in find_by_department(db_path, "IT")}
    assert rows == {"E0001": 9_000_000, "E0002": 6_000_000}


def test_raw_mass_raise_unknown_department(seeded: HRService, db_path: Path) -> None:
    with pytest.raises(LookupError):
        raise_salary_raw(db_path, "SALES", 5)


def test_ddl_contains_keys(seeded: HRService, db_path: Path) -> None:
    departments, employees = table_ddl(db_path)
    assert "PRIMARY KEY (id)" in departments and "UNIQUE (code)" in departments
    assert "REFERENCES departments (id) ON DELETE RESTRICT" in employees
    assert "CONSTRAINT ck_employees_salary_range CHECK" in employees
