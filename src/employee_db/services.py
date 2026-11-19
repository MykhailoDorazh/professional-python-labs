"""Service layer: HR business rules; persistence is delegated to repositories."""

from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from employee_db.database import transaction
from employee_db.exceptions import (
    DepartmentNotEmptyError,
    DepartmentNotFoundError,
    EmployeeNotFoundError,
    HRError,
    InvalidSalaryError,
)
from employee_db.models import Department, Employee
from employee_db.money import MAX_SALARY_CENTS, from_cents, to_cents
from employee_db.repositories import DepartmentRepository, EmployeeRepository

PERSONNEL_NUMBER_RE = re.compile(r"E\d{4}")


class HRService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.departments = DepartmentRepository(session)
        self.employees = EmployeeRepository(session)

    # ---------- departments ----------
    def create_department(self, code: str, name: str) -> Department:
        if not code.strip() or not name.strip():
            raise HRError("Код і назва відділу обов'язкові")
        with transaction(self.session):
            return self.departments.add(Department(code=code.strip().upper(), name=name.strip()))

    def get_department(self, code: str) -> Department:
        department = self.departments.get_by_code(code)
        if department is None:
            raise DepartmentNotFoundError(f"Відділ {code} не знайдено")
        return department

    def rename_department(self, code: str, name: str) -> Department:
        with transaction(self.session):
            department = self.get_department(code)
            department.name = name
            return department

    def delete_department(self, code: str) -> None:
        """Only an empty department can be deleted (FOREIGN KEY ... ON DELETE RESTRICT)."""
        with transaction(self.session):
            department = self.get_department(code)
            try:
                self.departments.delete(department)
            except IntegrityError as error:
                raise DepartmentNotEmptyError(f"У відділі {code} ще є працівники") from error

    # ---------- employees: CRUD ----------
    def hire(self, personnel_number: str, full_name: str, position: str,
             salary: Decimal | str | int, department_code: str,
             hire_date: date | None = None) -> Employee:
        number = personnel_number.strip().upper()
        if not PERSONNEL_NUMBER_RE.fullmatch(number):
            raise HRError(f"Некоректний табельний номер: {personnel_number!r}")
        if not full_name.strip() or not position.strip():
            raise HRError("ПІБ і посада обов'язкові")
        cents = self._salary(salary)
        with transaction(self.session):
            department = self.get_department(department_code)
            return self.employees.add(Employee(
                personnel_number=number, full_name=" ".join(full_name.split()),
                position=position.strip(), salary_cents=cents,
                department_id=department.id, hire_date=hire_date))

    def get_employee(self, personnel_number: str) -> Employee:
        employee = self.employees.get_by_number(personnel_number)
        if employee is None:
            raise EmployeeNotFoundError(f"Працівника {personnel_number} не знайдено")
        return employee

    def list_employees(self) -> list[Employee]:
        return self.employees.filter()

    def employees_in(self, department_code: str) -> list[Employee]:
        """Search by department."""
        return self.employees.list_by_department(self.get_department(department_code).id)

    def change_position(self, personnel_number: str, position: str) -> Employee:
        if not position.strip():
            raise HRError("Посада не може бути порожньою")
        with transaction(self.session):
            employee = self.get_employee(personnel_number)
            employee.position = position.strip()
            return employee

    def change_salary(self, personnel_number: str, salary: Decimal | str | int) -> Employee:
        cents = self._salary(salary)
        with transaction(self.session):
            employee = self.get_employee(personnel_number)
            employee.salary_cents = cents
            return employee

    def transfer(self, personnel_number: str, department_code: str) -> Employee:
        with transaction(self.session):
            employee = self.get_employee(personnel_number)
            employee.department_id = self.get_department(department_code).id
            return employee

    def fire(self, personnel_number: str) -> None:
        with transaction(self.session):
            self.employees.delete(self.get_employee(personnel_number))

    # ---------- mass operations: one transaction, all or nothing ----------
    def transfer_many(self, personnel_numbers: list[str], department_code: str) -> int:
        """Move several employees to another department atomically."""
        with transaction(self.session):
            target = self.get_department(department_code)
            for number in personnel_numbers:
                # unknown number -> exception -> ROLLBACK of the already moved ones
                self.get_employee(number).department_id = target.id
                self.session.flush()
            return len(personnel_numbers)

    def raise_salaries(self, department_code: str, percent: Decimal | str | int) -> int:
        """Raise salaries of the whole department by `percent` in one transaction.
        If any new salary breaks the CHECK constraint, nothing is changed."""
        factor = 1 + Decimal(str(percent)) / 100
        if factor <= 0:
            raise InvalidSalaryError(f"Некоректний відсоток: {percent}")
        with transaction(self.session):
            # від меншої зарплати до більшої: збій на останньому показує відкат попередніх
            employees = sorted(self.employees_in(department_code), key=lambda e: e.salary_cents)
            for employee in employees:
                employee.salary_cents = int(
                    (employee.salary_cents * factor).quantize(Decimal("1"), ROUND_HALF_UP))
                try:
                    self.session.flush()  # UPDATE; the database checks the salary range
                except IntegrityError as error:
                    raise InvalidSalaryError(
                        f"Нова зарплата {employee.personnel_number} перевищує максимум") from error
            return len(employees)

    # ---------- reports ----------
    def payroll(self, department_code: str | None = None) -> Decimal:
        return from_cents(self.employees.payroll_cents(self._department_id(department_code)))

    def average_salary(self, department_code: str | None = None) -> Decimal:
        value = self.employees.average_cents(self._department_id(department_code))
        return from_cents(round(value)) if value is not None else Decimal("0.00")

    def highest_paid(self, department_code: str | None = None) -> Employee | None:
        return self.employees.highest_paid(self._department_id(department_code))

    def department_stats(self) -> list[tuple[str, str, int, Decimal, Decimal, Decimal]]:
        return [(code, name, count, from_cents(total), from_cents(round(avg)), from_cents(top))
                for code, name, count, total, avg, top in self.employees.stats_by_department()]

    # ---------- internal ----------
    def _department_id(self, department_code: str | None) -> int | None:
        return None if department_code is None else self.get_department(department_code).id

    @staticmethod
    def _salary(salary: Decimal | str | int) -> int:
        cents = to_cents(salary)
        if cents > MAX_SALARY_CENTS:
            raise InvalidSalaryError(f"Зарплата перевищує 1 000 000.00: {salary}")
        return cents
