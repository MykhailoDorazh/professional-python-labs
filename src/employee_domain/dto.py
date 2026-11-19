"""External payloads (TypedDict) and their mapping to domain objects."""

from typing import Literal, NotRequired, TypedDict

from employee_domain.models import Developer, Employee, Level, Manager
from employee_domain.value_objects import Money


class EmployeePayload(TypedDict):
    """JSON-like employee data from an external system (still a plain dict)."""

    employee_id: str
    name: str
    position: str
    role: Literal["employee", "manager", "developer"]
    department: str
    salary: float
    currency: str
    bonus_rate: NotRequired[float]
    level: NotRequired[Level]


class DepartmentStats(TypedDict):
    employees: int
    payroll: float
    average: float


class SummaryPayload(TypedDict):
    employees: int
    payroll: float
    average_salary: float
    highest_paid: str | None
    currency: str
    by_department: dict[str, DepartmentStats]


def employee_from_payload(data: EmployeePayload) -> Employee:
    """Payload -> domain object (validation happens in the constructors)."""
    salary = Money(data["salary"], data["currency"])
    args = (data["employee_id"], data["name"], data["position"], salary)
    if data["role"] == "manager":
        return Manager(*args, bonus_rate=data.get("bonus_rate", 0.2))
    if data["role"] == "developer":
        return Developer(*args, level=data.get("level", "middle"))
    return Employee(*args)


def employee_to_payload(employee: Employee) -> EmployeePayload:
    payload: EmployeePayload = {
        "employee_id": employee.employee_id,
        "name": employee.name,
        "position": employee.position,
        "role": "employee",
        "department": employee.department or "",
        "salary": employee.salary.amount,
        "currency": employee.salary.currency,
    }
    if isinstance(employee, Manager):
        payload["role"] = "manager"
        payload["bonus_rate"] = employee.bonus_rate
    elif isinstance(employee, Developer):
        payload["role"] = "developer"
        payload["level"] = employee.level
    return payload
