"""Data model of the employee management system."""

import re
from dataclasses import dataclass

from employee_manager.config import CURRENCY, EMPLOYEE_ID_PATTERN, MAX_SALARY, MIN_SALARY
from employee_manager.exceptions import InvalidEmployeeError, InvalidSalaryError


def validate_salary(salary: float) -> float:
    """Check that the salary is in the allowed range and round it to cents."""
    if not MIN_SALARY <= salary <= MAX_SALARY:
        raise InvalidSalaryError(
            f"Зарплата має бути в межах {MIN_SALARY:.0f}..{MAX_SALARY:.0f}: {salary}"
        )
    return round(salary, 2)


@dataclass
class Employee:
    """Employee: id, name, position, department and monthly salary."""

    employee_id: str
    name: str
    position: str
    department: str
    salary: float

    def __post_init__(self) -> None:
        self.employee_id = self.employee_id.strip().upper()
        self.name = self.name.strip()
        self.position = self.position.strip()
        self.department = self.department.strip()

        if not re.fullmatch(EMPLOYEE_ID_PATTERN, self.employee_id):
            raise InvalidEmployeeError(
                f"Некоректний табельний номер: {self.employee_id!r} (очікується E1234)"
            )
        for field, value in (("ПІБ", self.name), ("посада", self.position),
                             ("відділ", self.department)):
            if not value:
                raise InvalidEmployeeError(f"Поле «{field}» не може бути порожнім")
        self.salary = validate_salary(self.salary)

    @property
    def formatted_salary(self) -> str:
        return f"{self.salary:,.2f} {CURRENCY}".replace(",", " ")
