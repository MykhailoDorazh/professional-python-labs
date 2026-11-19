"""Application services and simple adapters."""

import logging
from collections.abc import Iterable
from itertools import count

from employee_app.exceptions import (
    DepartmentNotFoundError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
)
from employee_app.models import Department, Employee, PayrollRecord
from employee_app.protocols import EmployeeReader, EmployeeStore, Notifier
from employee_app.repositories import InMemoryRepository
from employee_app.value_objects import Money

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"    [notify -> {recipient}] {message}")


class HRService:
    """Use cases: add employee to a department, search, salary change, transfer.
    Dependencies are injected (repositories, notifier)."""

    def __init__(self, employees: EmployeeStore, departments: InMemoryRepository[Department],
                 notifier: Notifier) -> None:
        self._employees = employees
        self._departments = departments
        self._notifier = notifier
        self.failed_notifications = 0

    def department(self, code: str) -> Department:
        department = self._departments.get(code)
        if department is None:
            raise DepartmentNotFoundError(f"Відділ {code} не знайдено")
        return department

    def add_employee(self, employee: Employee, department_code: str) -> Employee:
        department = self.department(department_code)
        if self._employees.get(employee.employee_id) is not None:
            raise DuplicateEmployeeError(f"Працівник {employee.employee_id} вже існує")
        self._employees.add(employee)
        department.add(employee)
        self._notify(employee, f"зараховано до відділу «{department.name}»")
        return employee

    def find_employee(self, employee_id: str) -> Employee:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(f"Працівника {employee_id} не знайдено")
        return employee

    def find_by_department(self, code: str) -> list[Employee]:
        return sorted(self.department(code), key=lambda e: e.employee_id)

    def change_salary(self, employee_id: str, new_salary: Money) -> Employee:
        employee = self.find_employee(employee_id)
        employee.change_salary(new_salary)
        self._notify(employee, "оклад змінено")  # без суми: зарплата конфіденційна
        return employee

    def transfer(self, employee_id: str, department_code: str) -> Employee:
        employee = self.find_employee(employee_id)
        target = self.department(department_code)
        if employee.department:
            self.department(employee.department).remove(employee)
        target.add(employee)
        self._notify(employee, f"переведено до відділу «{target.name}»")
        return employee

    def _notify(self, employee: Employee, text: str) -> None:
        """A failed notification must not cancel a completed HR operation."""
        try:
            self._notifier.send(employee.employee_id, text)
        except Exception as error:  # зовнішня система: будь-яка її помилка
            self.failed_notifications += 1
            logger.warning("Notification for %s failed: %s", employee.employee_id, error)


class PayrollService:
    """Statistics and payroll; depends only on the read interface (ISP)."""

    def __init__(self, employees: EmployeeReader) -> None:
        self._employees = employees
        self._record_ids = count(1)

    def _items(self, employees: Iterable[Employee] | None) -> list[Employee]:
        return list(self._employees if employees is None else employees)

    def total_payroll(self, employees: Iterable[Employee] | None = None) -> Money:
        return sum((e.salary for e in self._items(employees)), start=Money.zero())

    def average_salary(self, employees: Iterable[Employee] | None = None) -> Money:
        items = self._items(employees)
        return self.total_payroll(items) / len(items) if items else Money.zero()

    def highest_paid(self, employees: Iterable[Employee] | None = None) -> Employee | None:
        return max(self._items(employees), default=None)

    def run_payroll(self, period: str) -> list[PayrollRecord]:
        return [e.payroll(next(self._record_ids), period) for e in self._employees]

    def by_department(self) -> dict[str, dict[str, float]]:
        groups: dict[str, list[Employee]] = {}
        for employee in self._employees:
            groups.setdefault(employee.department or "-", []).append(employee)
        return {code: {"employees": len(items),
                       "payroll": self.total_payroll(items).amount,
                       "average": self.average_salary(items).amount}
                for code, items in sorted(groups.items())}
