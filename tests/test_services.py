"""Tests of the business logic (run: python -m unittest discover tests)."""

import unittest

from employee_manager.exceptions import (
    EmployeeNotFoundError,
    InvalidEmployeeError,
    InvalidSalaryError,
)
from employee_manager.models import Employee
from employee_manager.services import (
    add_employee,
    average_salary,
    calculate_statistics,
    change_salary,
    department_summary,
    find_by_department,
    find_employee,
    highest_paid,
    search_employees,
    sort_employees,
    total_payroll,
    transfer,
)


def make_employees() -> list[Employee]:
    return [
        Employee("E1001", "Іван Петренко", "Розробник", "IT", 50_000),
        Employee("E1002", "Олена Коваль", "Тімлід", "IT", 70_000),
        Employee("E1003", "Андрій Мельник", "Бухгалтер", "Фінанси", 30_000),
    ]


class ServicesTest(unittest.TestCase):
    def test_payroll_average_and_max(self) -> None:
        employees = make_employees()
        self.assertEqual(total_payroll(employees), 150_000)
        self.assertEqual(average_salary(employees), 50_000)
        top = highest_paid(employees)
        self.assertIsNotNone(top)
        self.assertEqual(top.employee_id, "E1002")  # type: ignore[union-attr]

    def test_empty_list(self) -> None:
        self.assertEqual(average_salary([]), 0.0)
        self.assertIsNone(highest_paid([]))
        self.assertEqual(calculate_statistics([])["count"], 0)

    def test_find_by_department(self) -> None:
        found = find_by_department(make_employees(), " it ")
        self.assertEqual([e.employee_id for e in found], ["E1001", "E1002"])
        self.assertEqual(find_by_department(make_employees(), "HR"), [])

    def test_find_employee(self) -> None:
        self.assertEqual(find_employee(make_employees(), "e1003").name, "Андрій Мельник")
        with self.assertRaises(EmployeeNotFoundError):
            find_employee(make_employees(), "E9999")

    def test_change_salary_validation(self) -> None:
        employee = make_employees()[0]
        self.assertEqual(change_salary(employee, 0), 0)  # boundary value is allowed
        with self.assertRaises(InvalidSalaryError):
            change_salary(employee, -0.01)
        self.assertEqual(employee.salary, 0)

    def test_transfer_and_summary(self) -> None:
        employees = make_employees()
        transfer(employees[0], "Фінанси")
        self.assertEqual(department_summary(employees),
                         {"IT": (1, 70_000.0), "Фінанси": (2, 80_000.0)})

    def test_search_and_sort(self) -> None:
        found = search_employees(make_employees(), "о", min_salary=40_000)
        self.assertEqual([e.employee_id for e in found], ["E1001", "E1002"])
        self.assertEqual(sort_employees(make_employees())[0].employee_id, "E1002")

    def test_add_employee_validation(self) -> None:
        employees = make_employees()
        with self.assertRaises(InvalidEmployeeError):
            add_employee(employees, Employee("E1001", "Тест", "Тест", "IT", 1))
        with self.assertRaises(InvalidEmployeeError):
            Employee("12345", "Тест", "Тест", "IT", 1)
        with self.assertRaises(InvalidEmployeeError):
            Employee("E1009", "Тест", "  ", "IT", 1)


if __name__ == "__main__":
    unittest.main()
