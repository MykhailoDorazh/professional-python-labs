"""Application/service layer, report abstraction and concrete adapters."""

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import count
from typing import TypeVar

from employee_domain.dto import DepartmentStats, SummaryPayload
from employee_domain.exceptions import (
    DepartmentNotFoundError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
)
from employee_domain.models import Department, Employee, PayrollRecord
from employee_domain.protocols import EmployeeReader, EmployeeStore, Notifier
from employee_domain.repositories import InMemoryRepository
from employee_domain.value_objects import DEFAULT_CURRENCY, Money

Number = TypeVar("Number", int, float)  # constrained TypeVar


def clamp(value: Number, low: Number, high: Number) -> Number:
    """Keep value in [low, high]; result has the same type as the input."""
    return max(low, min(value, high))


# ---------- concrete notifiers (не успадковують Notifier: structural typing) ----------

class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"    [notify -> {recipient}] {message}")


class InMemoryNotifier:
    """Stores messages instead of sending them (useful for tests)."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))


# ---------- application services ----------

class HRService:
    """Use cases: add employee to a department, search, salary change, transfer.
    Dependencies are injected through the constructor (DIP)."""

    def __init__(self, employees: EmployeeStore, departments: InMemoryRepository[Department],
                 notifier: Notifier) -> None:
        self._employees = employees
        self._departments = departments
        self._notifier = notifier

    def department(self, code: str) -> Department:
        department = self._departments.get(code)
        if department is None:
            raise DepartmentNotFoundError(f"Відділ {code} не знайдено")
        return department

    def add_employee(self, employee: Employee, department_code: str) -> Employee:
        """Add a new employee and assign the department."""
        department = self.department(department_code)  # спочатку перевірка відділу
        if self._employees.get(employee.employee_id) is not None:
            raise DuplicateEmployeeError(f"Працівник {employee.employee_id} вже існує")
        self._employees.add(employee)
        department.add(employee)
        self._notifier.send(employee.employee_id,
                            f"Вас зараховано до відділу «{department.name}»")
        return employee

    def find_employee(self, employee_id: str) -> Employee:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(f"Працівника {employee_id} не знайдено")
        return employee

    def find_by_department(self, code: str) -> list[Employee]:
        return sorted(self.department(code), key=lambda e: e.employee_id)

    def search(self, text: str) -> list[Employee]:
        text = text.lower()
        return [e for e in self._employees
                if text in e.name.lower() or text in e.position.lower()]

    def change_salary(self, employee_id: str, new_salary: Money) -> Employee:
        employee = self.find_employee(employee_id)
        employee.change_salary(new_salary)
        # у повідомленні немає суми - зарплата є конфіденційними даними
        self._notifier.send(employee_id, "Ваш оклад змінено, деталі в розрахунковому листі")
        return employee

    def transfer(self, employee_id: str, department_code: str) -> Employee:
        employee = self.find_employee(employee_id)
        target = self.department(department_code)
        if employee.department:
            self.department(employee.department).remove(employee)
        target.add(employee)
        self._notifier.send(employee_id, f"Вас переведено до відділу «{target.name}»")
        return employee


class PayrollService:
    """Payroll calculation and statistics; depends only on the read interface (ISP)."""

    _record_ids = count(1)

    def __init__(self, employees: EmployeeReader) -> None:
        self._employees = employees

    def run_payroll(self, period: str) -> list[PayrollRecord]:
        return [e.payroll(next(self._record_ids), period) for e in self._employees]

    def total_payroll(self, employees: Iterable[Employee] | None = None) -> Money:
        items = self._employees if employees is None else employees
        return sum((e.salary for e in items), start=Money.zero())

    def average_salary(self, employees: Iterable[Employee] | None = None) -> Money:
        items = list(self._employees if employees is None else employees)
        return self.total_payroll(items) / len(items) if items else Money.zero()

    def highest_paid(self, employees: Iterable[Employee] | None = None) -> Employee | None:
        items = self._employees if employees is None else employees
        return max(items, default=None)  # Employee.__lt__ порівнює зарплати

    def ranking(self) -> list[Employee]:
        return sorted(self._employees, reverse=True)

    def by_department(self) -> dict[str, DepartmentStats]:
        groups: dict[str, list[Employee]] = {}
        for employee in self._employees:
            groups.setdefault(employee.department or "-", []).append(employee)
        return {code: {"employees": len(items),
                       "payroll": self.total_payroll(items).amount,
                       "average": self.average_salary(items).amount}
                for code, items in sorted(groups.items())}

    def summary(self) -> SummaryPayload:
        top = self.highest_paid()
        return {
            "employees": len(list(self._employees)),
            "payroll": self.total_payroll().amount,
            "average_salary": self.average_salary().amount,
            "highest_paid": top.employee_id if top else None,
            "currency": DEFAULT_CURRENCY,
            "by_department": self.by_department(),
        }


# ---------- report abstraction (ABC + Template Method) ----------

class ReportFormatter(ABC):
    """Abstract report: the order of sections is fixed, the format is not."""

    def render(self, summary: SummaryPayload) -> str:
        return "\n".join([self.header(), self.body(summary)])

    @abstractmethod
    def header(self) -> str: ...

    @abstractmethod
    def body(self, summary: SummaryPayload) -> str: ...


class TextReport(ReportFormatter):
    def header(self) -> str:
        return "Звіт з фонду оплати праці"

    def body(self, summary: SummaryPayload) -> str:
        lines = [f"  працівників: {summary['employees']}, фонд: {summary['payroll']:.2f}, "
                 f"середня: {summary['average_salary']:.2f} {summary['currency']}"]
        for code, stats in summary["by_department"].items():
            lines.append(f"  {code:<6} {stats['employees']:>2} осіб  фонд {stats['payroll']:>10.2f}"
                         f"  середня {stats['average']:>9.2f}")
        return "\n".join(lines)


class JsonReport(ReportFormatter):
    def header(self) -> str:
        return "payroll-report v1"

    def body(self, summary: SummaryPayload) -> str:
        return json.dumps(summary, ensure_ascii=False)
