"""Tests of the domain model (run: python -m unittest discover tests)."""

import unittest

from employee_domain.dto import employee_from_payload, employee_to_payload
from employee_domain.exceptions import (
    CurrencyMismatchError,
    DepartmentNotFoundError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
    InvalidEmployeeError,
    InvalidSalaryError,
)
from employee_domain.models import Department, Developer, Employee, Manager
from employee_domain.repositories import InMemoryRepository
from employee_domain.services import HRService, InMemoryNotifier, PayrollService, TextReport
from employee_domain.value_objects import Money


class DomainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.employees: InMemoryRepository[Employee] = InMemoryRepository()
        departments: InMemoryRepository[Department] = InMemoryRepository()
        departments.add(Department("IT", "Інформаційні технології"))
        departments.add(Department("HR", "Персонал"))
        self.notifier = InMemoryNotifier()
        self.hr = HRService(self.employees, departments, self.notifier)
        self.payroll = PayrollService(self.employees)
        self.lead = Manager("E0001", "Олена Коваль", "Тімлід", Money(90_000), bonus_rate=0.1)
        self.hr.add_employee(self.lead, "IT")
        self.hr.add_employee(
            Developer("E0002", "Іван Петренко", "Розробник", Money(60_000), level="senior"), "IT")
        self.hr.add_employee(Employee("E0003", "Марія Бондар", "HR-менеджер", Money(30_000)), "HR")

    def test_money_is_immutable_value_object(self) -> None:
        self.assertEqual(Money(1) + Money(2.5), Money(3.5))
        with self.assertRaises(ValueError):
            Money(-1)
        with self.assertRaises(CurrencyMismatchError):
            Money(1) + Money(1, "USD")

    def test_validation(self) -> None:
        with self.assertRaises(InvalidEmployeeError):
            Employee("12345", "Олег", "Аналітик", Money(1))
        with self.assertRaises(InvalidEmployeeError):
            Employee("E0009", " ", "Аналітик", Money(1))
        with self.assertRaises(InvalidSalaryError):
            Employee("E0009", "Олег", "Аналітик", Money(1_000_001))
        Employee("E0009", "Олег", "Аналітик", Money(0))  # boundary value is valid

    def test_department_assignment_and_search(self) -> None:
        self.assertEqual([e.employee_id for e in self.hr.find_by_department("it")],
                         ["E0001", "E0002"])
        self.assertEqual(self.hr.find_employee("e0003").department, "HR")
        with self.assertRaises(DepartmentNotFoundError):
            self.hr.add_employee(Employee("E0004", "Тарас Новак", "Логіст", Money(1)), "LOG")
        self.assertNotIn("E0004", self.employees)  # not added when the department is wrong
        with self.assertRaises(DuplicateEmployeeError):
            self.hr.add_employee(Employee("E0002", "Дублікат", "Тестувальник", Money(1)), "IT")
        with self.assertRaises(EmployeeNotFoundError):
            self.hr.find_employee("E9999")

    def test_statistics(self) -> None:
        self.assertEqual(self.payroll.total_payroll(), Money(180_000))
        self.assertEqual(self.payroll.average_salary(), Money(60_000))
        top = self.payroll.highest_paid()
        self.assertEqual(top.employee_id if top else None, "E0001")
        self.assertEqual(self.payroll.average_salary([]), Money(0))
        self.assertEqual(self.payroll.by_department()["IT"]["payroll"], 150_000)

    def test_salary_change_transfer_and_notifications(self) -> None:
        self.hr.change_salary("E0003", Money(35_000))
        self.hr.transfer("E0003", "IT")
        it = self.hr.find_by_department("IT")
        self.assertEqual(len(it), 3)
        self.assertEqual(self.hr.find_by_department("HR"), [])
        self.assertEqual(len(self.notifier.messages), 5)
        self.assertNotIn("35", self.notifier.messages[3][1])  # salary is not disclosed

    def test_polymorphic_bonus_and_reports(self) -> None:
        self.lead.add_to_team(self.hr.find_employee("E0002"))
        records = {r.employee_id: r for r in self.payroll.run_payroll("2026-11")}
        self.assertEqual(records["E0001"].bonus, Money(9_500))  # 10 % + 500 per team member
        self.assertEqual(records["E0002"].bonus, Money(9_000))  # senior: 15 %
        self.assertEqual(records["E0003"].total, Money(30_000))
        self.assertIn("IT", TextReport().render(self.payroll.summary()))
        payload = employee_to_payload(self.lead)
        self.assertEqual(employee_from_payload(payload), self.lead)


if __name__ == "__main__":
    unittest.main()
