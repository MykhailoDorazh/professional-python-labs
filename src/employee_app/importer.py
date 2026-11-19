"""CSV import of employees (streaming, strict/tolerant)."""

import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from employee_app.config import AppConfig
from employee_app.exceptions import DataImportError, EmployeeError, RecordValidationError
from employee_app.models import Developer, Employee, Manager
from employee_app.value_objects import Money

logger = logging.getLogger(__name__)
ROLES = ("employee", "manager", "developer")


@dataclass(frozen=True, slots=True)
class EmployeeRecord:
    line_number: int
    department: str
    employee: Employee


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    errors: list[str] = field(default_factory=list)


def read_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            for line_number, row in enumerate(csv.DictReader(file), start=2):
                yield line_number, row
    except OSError as error:
        raise DataImportError(f"Cannot read {path}") from error


def parse_salary(text: str | None, *, line_number: int, config: AppConfig) -> Money:
    try:
        value = float(text or "")
    except ValueError as error:
        raise RecordValidationError("salary must be numeric", line_number=line_number,
                                    field="salary") from error
    if not config.min_salary <= value <= config.max_salary:
        raise RecordValidationError("salary out of range", line_number=line_number,
                                    field="salary")
    return Money(value, config.currency)


def parse_employee(row: dict[str, str], line_number: int, config: AppConfig) -> EmployeeRecord:
    department = (row.get("department") or "").strip().upper()
    if department not in config.departments:
        raise RecordValidationError(f"Department {department!r} is not configured",
                                    line_number=line_number, field="department")
    role = (row.get("role") or "employee").strip().lower()
    if role not in ROLES:
        raise RecordValidationError(f"Unknown role {role!r}", line_number=line_number,
                                    field="role")
    salary = parse_salary(row.get("salary"), line_number=line_number, config=config)
    try:
        args = (row["employee_id"], row["name"], row["position"], salary)
        employee: Employee
        if role == "manager":
            employee = Manager(*args)
        elif role == "developer":
            employee = Developer(*args)
        else:
            employee = Employee(*args)
    except (KeyError, EmployeeError) as error:
        raise RecordValidationError(f"Invalid employee record: {error}",
                                    line_number=line_number) from error
    return EmployeeRecord(line_number, department, employee)


def read_employees(path: Path, config: AppConfig,
                   statistics: ImportStatistics) -> Iterator[EmployeeRecord]:
    for line_number, row in read_rows(path):
        statistics.total += 1
        try:
            record = parse_employee(row, line_number, config)
        except RecordValidationError as error:
            statistics.invalid += 1
            statistics.errors.append(f"line {line_number}: {error}")
            logger.warning("Invalid employee at line %s: %s", line_number, error)
            if config.skip_invalid:
                continue
            raise
        statistics.valid += 1
        yield record
