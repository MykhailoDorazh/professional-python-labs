"""Processing of employee records: search, index, grouping, filtering, sorting."""

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from employee_analytics.decorators import log_operation

Employee = dict[str, Any]
Predicate = Callable[[Employee], bool]


# ---------- пошук ----------

def find_employee_linear(employees: list[Employee], employee_id: str) -> Employee | None:
    """Linear search in a list. Complexity: O(n)."""
    for employee in employees:
        if employee["id"] == employee_id:
            return employee
    return None


def create_employee_index(employees: list[Employee]) -> dict[str, Employee]:
    """dict-index by employee id (dict comprehension). Build: O(n)."""
    return {employee["id"]: employee for employee in employees}


@log_operation("пошук за табельним номером")
def find_by_id(index: dict[str, Employee], employee_id: str) -> Employee | None:
    """Search in the dict-index. Complexity: O(1) on average."""
    return index.get(employee_id)


def find_by_name(employees: list[Employee], text: str) -> list[Employee]:
    """Employees whose name contains the text (case-insensitive)."""
    needle = text.lower()
    return [e for e in employees if needle in e["name"].lower()]


# ---------- множини ----------

def get_positions(employees: list[Employee]) -> set[str]:
    """Unique positions (set comprehension). O(n)."""
    return {employee["position"] for employee in employees}


def get_used_departments(employees: list[Employee]) -> set[str]:
    """Departments that actually have employees."""
    return {employee["department"] for employee in employees}


# ---------- групування ----------

@log_operation("групування за відділом")
def group_by_department(employees: list[Employee]) -> dict[str, list[Employee]]:
    """Group employees by department using defaultdict(list). O(n)."""
    groups: defaultdict[str, list[Employee]] = defaultdict(list)
    for employee in employees:
        groups[employee["department"]].append(employee)
    return dict(groups)


def group_nested(employees: list[Employee]) -> dict[str, dict[str, list[str]]]:
    """Nested grouping: department -> position -> list of employee ids."""
    result: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for employee in employees:
        result[employee["department"]][employee["position"]].append(employee["id"])
    return {department: dict(positions) for department, positions in result.items()}


def count_by_department(employees: list[Employee]) -> Counter[str]:
    """Number of employees in every department (Counter + generator expression)."""
    return Counter(employee["department"] for employee in employees)


# ---------- фільтрація ----------

def filter_items(items: list[Employee], predicate: Predicate) -> list[Employee]:
    """Universal filter: keeps items for which predicate(item) is True."""
    return [item for item in items if predicate(item)]


def make_min_salary_filter(minimum: float) -> Predicate:
    """Closure: the inner function remembers `minimum`."""

    def predicate(employee: Employee) -> bool:
        return employee["salary"] >= minimum

    return predicate


def make_department_filter(*departments: str) -> Predicate:
    """Closure over *args: the department must be one of the given ones."""
    allowed = set(departments)

    def predicate(employee: Employee) -> bool:
        return employee["department"] in allowed

    return predicate


@log_operation("фільтрація за мінімальною зарплатою")
def filter_by_min_salary(employees: list[Employee], minimum: float) -> list[Employee]:
    """Employees with salary >= minimum."""
    return filter_items(employees, make_min_salary_filter(minimum))


# ---------- сортування ----------

def sort_items(items: list[Employee], *keys: str, reverse: bool = False) -> list[Employee]:
    """Universal sorting by one or several fields. O(n log n)."""
    return sorted(items, key=lambda item: tuple(item[k] for k in keys), reverse=reverse)


@log_operation("сортування за зарплатою")
def sort_by_salary(employees: list[Employee], descending: bool = True) -> list[Employee]:
    """Sort employees by salary (lambda as the key)."""
    return sorted(employees, key=lambda employee: employee["salary"], reverse=descending)


# ---------- конвеєр ----------

def pipeline(data: list[Employee],
             *steps: Callable[[list[Employee]], list[Employee]]) -> list[Employee]:
    """Apply processing steps one after another."""
    for step in steps:
        data = step(data)
    return data
