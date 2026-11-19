"""Lazy filtering and search."""

from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

from employee_stream.models import Employee

T = TypeVar("T")


def filter_by_department(employees: Iterable[Employee], department: str) -> Iterator[Employee]:
    """Keep employees of the department (case-insensitive)."""
    name = department.strip().lower()
    for employee in employees:
        if employee.department.lower() == name:
            yield employee


def filter_by_salary(
    employees: Iterable[Employee],
    minimum: float = 0.0,
    maximum: float = float("inf"),
) -> Iterator[Employee]:
    """Lazy filter by salary level: keep salaries in [minimum, maximum]."""
    for employee in employees:
        if minimum <= employee.salary <= maximum:
            yield employee


def find_first(records: Iterable[T], predicate: Callable[[T], bool]) -> T | None:
    """Lazy search with early termination: stops at the first match."""
    for record in records:
        if predicate(record):
            return record
    return None


def find_employee(employees: Iterable[Employee], employee_id: str) -> Employee | None:
    """Search by employee_id (stops reading the file when found)."""
    key = employee_id.upper()
    return find_first(employees, lambda e: e.employee_id == key)
