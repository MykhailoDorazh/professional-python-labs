"""Validation of one employee record."""

import re

from employee_io.exceptions import RecordValidationError, SalaryValidationError
from employee_io.models import Employee, ProcessingConfig

EMPLOYEE_ID_RE = re.compile(r"E\d{6}")


def _text(row: dict[str, str], field: str, line_number: int, label: str) -> str:
    value = " ".join((row.get(field) or "").split())
    if not value:
        raise RecordValidationError(f"{label} is empty", line_number=line_number, field=field)
    return value


def _salary(row: dict[str, str], line_number: int, config: ProcessingConfig) -> float:
    try:
        salary = float(row["salary"])
    except KeyError as error:
        raise SalaryValidationError("Missing field salary", line_number=line_number,
                                    field="salary") from error
    except (TypeError, ValueError) as error:
        # значення зарплати не додаємо в повідомлення - воно потрапляє в логи
        raise SalaryValidationError("Salary must be numeric", line_number=line_number,
                                    field="salary") from error
    if salary < 0:
        raise SalaryValidationError("Salary must be >= 0", line_number=line_number,
                                    field="salary")
    if salary > config.max_salary:
        raise SalaryValidationError("Salary exceeds max_salary", line_number=line_number,
                                    field="salary")
    return round(salary, 2)


def parse_employee(row: dict[str, str], *, line_number: int,
                   config: ProcessingConfig) -> Employee:
    """Validate a raw row and build an Employee. Raises RecordValidationError."""
    employee_id = (row.get("employee_id") or "").strip().upper()
    if not EMPLOYEE_ID_RE.fullmatch(employee_id):
        raise RecordValidationError("Invalid employee_id (expected E + 6 digits)",
                                    line_number=line_number, field="employee_id")
    name = _text(row, "name", line_number, "Name")
    position = _text(row, "position", line_number, "Position")
    department = _text(row, "department", line_number, "Department")
    allowed = {d.casefold(): d for d in config.allowed_departments}
    if department.casefold() not in allowed:
        raise RecordValidationError(f"Department {department!r} is not allowed",
                                    line_number=line_number, field="department")
    salary = _salary(row, line_number, config)
    # назву відділу беремо з конфігурації: "продажі" -> "Продажі"
    return Employee(employee_id, name, position, allowed[department.casefold()], salary)
