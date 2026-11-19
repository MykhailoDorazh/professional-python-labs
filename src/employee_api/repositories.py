"""Repository Pattern: SQL details are hidden from the service layer.

Repositories only add/flush objects; COMMIT/ROLLBACK is decided by the caller
(``database.transaction``), so several repository calls form one transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from employee_api.exceptions import (
    DepartmentNotFoundError,
    DuplicateDepartmentError,
    DuplicateEmployeeError,
)
from employee_api.models import Base, Department, Employee

ModelT = TypeVar("ModelT", bound=Base)

UK_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"


def uk_key(text: str) -> tuple[tuple[int, int], ...]:
    """Sort key that follows the Ukrainian alphabet (А < ... < І < ... < Я)."""
    return tuple(
        (1, UK_ALPHABET.index(ch)) if ch in UK_ALPHABET else (0, ord(ch))
        for ch in text.lower()
    )


class SqlAlchemyRepository(Generic[ModelT]):
    """Generic CRUD for one ORM model."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()  # INSERT now -> primary key is assigned
        return entity

    def get_by_id(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def get_all(self, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        statement = select(self.model).order_by(self.model.id).offset(offset)  # type: ignore[attr-defined]
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model)) or 0


class DepartmentRepository(SqlAlchemyRepository[Department]):
    model = Department

    def add(self, entity: Department) -> Department:
        try:
            return super().add(entity)
        except IntegrityError as error:
            raise DuplicateDepartmentError(f"Відділ {entity.code} вже існує") from error

    def get_by_code(self, code: str) -> Department | None:
        return self.session.scalar(select(Department).where(Department.code == code.upper()))


class EmployeeRepository(SqlAlchemyRepository[Employee]):
    model = Employee

    def add(self, entity: Employee) -> Employee:
        """INSERT an employee; translate DB constraint errors into domain errors.

        The caller's ``transaction()`` block performs the ROLLBACK.
        """
        try:
            return super().add(entity)
        except IntegrityError as error:
            message = str(error.orig)
            if "UNIQUE" in message:
                raise DuplicateEmployeeError(
                    f"Працівник {entity.personnel_number} вже існує") from error
            if "FOREIGN KEY" in message:
                raise DepartmentNotFoundError(
                    f"Відділу id={entity.department_id} не існує") from error
            raise

    def get_by_number(self, personnel_number: str) -> Employee | None:
        return self.session.scalar(
            select(Employee).where(Employee.personnel_number == personnel_number.upper()))

    def list_by_department(self, department_id: int) -> list[Employee]:
        statement = (select(Employee).where(Employee.department_id == department_id)
                     .order_by(Employee.personnel_number))
        return list(self.session.scalars(statement))

    def search(self, fragment: str) -> list[Employee]:
        # the pattern is sent as a bound parameter, not glued into SQL text
        statement = select(Employee).where(
            Employee.full_name.ilike(f"%{fragment}%") | Employee.position.ilike(f"%{fragment}%"))
        # SQLite ORDER BY compares code points: 'І' (U+0406) < 'А' (U+0410),
        # so the Ukrainian alphabetical order is applied in Python.
        return sorted(self.session.scalars(statement), key=lambda e: uk_key(e.full_name))

    def filter(self, *, min_salary_cents: int | None = None, position: str | None = None,
               order_by_salary: bool = False) -> list[Employee]:
        statement = select(Employee)
        if min_salary_cents is not None:
            statement = statement.where(Employee.salary_cents >= min_salary_cents)
        if position is not None:
            statement = statement.where(Employee.position == position)
        statement = statement.order_by(
            Employee.salary_cents.desc() if order_by_salary else Employee.personnel_number)
        return list(self.session.scalars(statement))

    def payroll_cents(self, department_id: int | None = None) -> int:
        statement = select(func.coalesce(func.sum(Employee.salary_cents), 0))
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        return self.session.scalar(statement) or 0

    def average_cents(self, department_id: int | None = None) -> float | None:
        statement = select(func.avg(Employee.salary_cents))
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        value = self.session.scalar(statement)
        return None if value is None else float(value)

    def highest_paid(self, department_id: int | None = None) -> Employee | None:
        statement = select(Employee).order_by(Employee.salary_cents.desc(),
                                              Employee.personnel_number).limit(1)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        return self.session.scalar(statement)

    def stats_by_department(self) -> Sequence[tuple[str, str, int, int, float, int]]:
        """JOIN departments-employees + GROUP BY: COUNT / SUM / AVG / MAX per department.
        LEFT JOIN keeps empty departments in the report."""
        statement = (
            select(
                Department.code,
                Department.name,
                func.count(Employee.id),
                func.coalesce(func.sum(Employee.salary_cents), 0),
                func.coalesce(func.avg(Employee.salary_cents), 0),
                func.coalesce(func.max(Employee.salary_cents), 0),
            )
            .join(Employee, Employee.department_id == Department.id, isouter=True)
            .group_by(Department.id)
            .order_by(Department.code)
        )
        return [(c, n, cnt, s, float(a), m) for c, n, cnt, s, a, m in self.session.execute(statement)]
