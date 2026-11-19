"""Database-level guarantees: CHECK, UNIQUE, FOREIGN KEY (enforced by SQLite PRAGMA)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from employee_db.database import transaction
from employee_db.models import Department, Employee
from employee_db.services import HRService


def test_check_constraint_forbids_negative_salary(seeded: HRService) -> None:
    """Even code that bypasses the service cannot store a negative salary."""
    with pytest.raises(IntegrityError, match="ck_employees_salary_range"):
        with transaction(seeded.session):
            seeded.session.execute(
                text("UPDATE employees SET salary_cents = -1 WHERE personnel_number = :n"),
                {"n": "E0001"})
    seeded.session.expire_all()
    assert seeded.get_employee("E0001").salary_cents == 9_000_000


def test_check_constraint_forbids_salary_above_max(seeded: HRService) -> None:
    with pytest.raises(IntegrityError, match="ck_employees_salary_range"):
        with transaction(seeded.session):
            seeded.get_employee("E0001").salary_cents = 100_000_001
            seeded.session.flush()


def test_check_constraint_on_empty_name(seeded: HRService) -> None:
    with pytest.raises(IntegrityError, match="ck_employees_name_not_empty"):
        with transaction(seeded.session):
            seeded.session.add(Employee(personnel_number="E0009", full_name="   ", position="X",
                                        salary_cents=0, department_id=1))


def test_unique_personnel_number(session: Session) -> None:
    with pytest.raises(IntegrityError, match="UNIQUE"):
        with transaction(session):
            department = Department(code="IT", name="ІТ")
            session.add(department)
            session.flush()
            session.add_all([
                Employee(personnel_number="E0001", full_name="А", position="X",
                         salary_cents=1, department_id=department.id),
                Employee(personnel_number="E0001", full_name="Б", position="X",
                         salary_cents=1, department_id=department.id)])


def test_foreign_key_is_enforced(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        with transaction(session):
            session.execute(text(
                "INSERT INTO employees (personnel_number, full_name, position, salary_cents, "
                "department_id) VALUES ('E0009', 'Ніхто', 'X', 0, 999)"))


def test_restrict_on_department_delete(seeded: HRService) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        with transaction(seeded.session):
            seeded.session.execute(text("DELETE FROM departments WHERE code = 'IT'"))
