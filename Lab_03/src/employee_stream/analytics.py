"""Aggregation stage: one pass, O(1) memory regardless of the data size."""

from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import accumulate
from typing import Any

from employee_stream.models import Employee


def calculate_statistics(employees: Iterable[Employee]) -> dict[str, Any]:
    """Count, payroll, average, highest/lowest paid, employees per department."""
    count = 0
    payroll = 0.0
    highest: Employee | None = None
    lowest: Employee | None = None
    departments: Counter[str] = Counter()
    for employee in employees:
        count += 1
        payroll += employee.salary
        departments[employee.department] += 1
        if highest is None or employee.salary > highest.salary:
            highest = employee
        if lowest is None or employee.salary < lowest.salary:
            lowest = employee
    return {
        "count": count,
        "payroll": round(payroll, 2),
        "average": round(payroll / count, 2) if count else 0.0,
        "highest": highest,
        "lowest": lowest,
        "departments": dict(departments.most_common()),
    }


def streaming_payroll(employees: Iterable[Employee]) -> float:
    """Payroll fund via a generator expression (no intermediate list)."""
    return round(sum(employee.salary for employee in employees), 2)


def running_payroll(employees: Iterable[Employee]) -> Iterator[float]:
    """Cumulative payroll after each employee (itertools.accumulate)."""
    return accumulate(employee.salary for employee in employees)


def streaming_average(values: Iterable[float]) -> float:
    """Average of a stream: only the running sum and the count are stored."""
    total, count = 0.0, 0
    for value in values:
        total += value
        count += 1
    return total / count if count else 0.0


def highest_paid(employees: Iterable[Employee]) -> Employee | None:
    """Employee with the maximum salary, found in one pass."""
    return max(employees, key=lambda e: e.salary, default=None)


def count_by_department(employees: Iterable[Employee]) -> Counter[str]:
    """Number of employees in every department (Counter over a generator)."""
    return Counter(employee.department for employee in employees)
