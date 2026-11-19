"""Aggregation and statistics of employee salaries."""

import json
from pathlib import Path
from typing import Any

from employee_analytics.data import DEPARTMENTS
from employee_analytics.decorators import log_operation, measure_time
from employee_analytics.processors import Employee, group_by_department


@measure_time
def total_payroll(employees: list[Employee]) -> float:
    """Payroll fund: sum of salaries (generator expression, no intermediate list)."""
    return round(sum(employee["salary"] for employee in employees), 2)


def average_salary(employees: list[Employee]) -> float:
    """Average salary."""
    if not employees:
        return 0.0
    return round(sum(e["salary"] for e in employees) / len(employees), 2)


@log_operation("пошук максимальної зарплати")
def highest_paid(employees: list[Employee]) -> Employee | None:
    """Employee with the highest salary (max + lambda). O(n)."""
    if not employees:
        return None
    return max(employees, key=lambda employee: employee["salary"])


def salary_range(employees: list[Employee]) -> tuple[float, float]:
    """(minimum, maximum) salary as an immutable tuple."""
    salaries = [employee["salary"] for employee in employees]
    return min(salaries), max(salaries)


def sum_values(*values: float) -> float:
    """Sum of any number of positional arguments (*args)."""
    return round(sum(values), 2)


def create_employee(**fields: Any) -> Employee:
    """Create an employee record from keyword arguments (**kwargs)."""
    required = {"id", "name", "position", "department", "salary"}
    missing = required - fields.keys()
    if missing:
        raise ValueError(f"Відсутні поля: {', '.join(sorted(missing))}")
    if fields["department"] not in DEPARTMENTS:
        raise ValueError(f"Невідомий відділ: {fields['department']}")
    if fields["salary"] < 0:
        raise ValueError("Зарплата не може бути від'ємною")
    return dict(fields)


def department_summary(employees: list[Employee]) -> dict[str, tuple[int, float, float]]:
    """department -> (count, payroll, average salary), built by dict comprehension."""
    groups = group_by_department(employees)
    return {
        department: (
            len(items),
            round(sum(e["salary"] for e in items), 2),
            round(sum(e["salary"] for e in items) / len(items), 2),
        )
        for department, items in groups.items()
    }


def export_summary(path: Path, **summary: Any) -> Path:
    """Export the summary to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
