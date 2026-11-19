"""Tests (run: python -m unittest discover tests)."""

import unittest

from employee_analytics.analytics import (
    average_salary,
    create_employee,
    department_summary,
    highest_paid,
    salary_range,
    sum_values,
    total_payroll,
)
from employee_analytics.data import employees
from employee_analytics.processors import (
    count_by_department,
    create_employee_index,
    filter_by_min_salary,
    find_by_id,
    find_employee_linear,
    get_positions,
    group_by_department,
    make_min_salary_filter,
    sort_by_salary,
)


class ProcessingTest(unittest.TestCase):
    def test_list_and_dict_search_agree(self) -> None:
        index = create_employee_index(employees)
        for employee in employees:
            self.assertIs(find_employee_linear(employees, employee["id"]),
                          find_by_id(index, employee["id"]))
        self.assertIsNone(find_by_id(index, "E0000"))

    def test_grouping_and_counting(self) -> None:
        groups = group_by_department(employees)
        counter = count_by_department(employees)
        self.assertEqual({d: len(v) for d, v in groups.items()}, dict(counter))
        self.assertEqual(len(get_positions(employees)), 8)

    def test_filter_and_sort(self) -> None:
        rich = sort_by_salary(filter_by_min_salary(employees, 50_000))
        self.assertEqual([e["id"] for e in rich], ["E1002", "E1010", "E1006", "E1001"])

    def test_closure_remembers_minimum(self) -> None:
        is_high = make_min_salary_filter(60_000)
        self.assertTrue(is_high({"salary": 60_000}))
        self.assertFalse(is_high({"salary": 59_999.99}))

    def test_aggregation(self) -> None:
        self.assertEqual(highest_paid(employees)["id"], "E1002")
        self.assertEqual(salary_range(employees), (27_500.0, 78_500.0))
        self.assertEqual(total_payroll(employees), 455_350.5)
        self.assertEqual(average_salary(employees), 45_535.05)
        self.assertEqual(sum_values(1, 2.5, 3), 6.5)
        self.assertEqual(department_summary(employees)["HR"], (2, 57_300.0, 28_650.0))

    def test_create_employee_validation(self) -> None:
        with self.assertRaises(ValueError):
            create_employee(id="E1", name="X", position="X", department="IT", salary=-1)
        with self.assertRaises(ValueError):
            create_employee(id="E1", name="X", position="X", department="Космос", salary=1)
        with self.assertRaises(ValueError):
            create_employee(id="E1", name="X")


if __name__ == "__main__":
    unittest.main()
