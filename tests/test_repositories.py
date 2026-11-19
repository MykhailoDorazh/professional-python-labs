"""Repository layer on a real SQLite test database."""

import pytest
from sqlalchemy.orm import Session

from employee_api.exceptions import (
    DepartmentNotFoundError,
    DuplicateDepartmentError,
    DuplicateEmployeeError,
)
from employee_api.models import Department, Employee
from employee_api.repositories import DepartmentRepository, EmployeeRepository, uk_key
from employee_api.services import HRService


def test_add_assigns_primary_key(session: Session) -> None:
    departments = DepartmentRepository(session)
    department = departments.add(Department(code="IT", name="ІТ"))
    assert department.id is not None
    assert departments.get_by_id(department.id) is department
    assert departments.get_by_code("it") is department
    assert departments.count() == 1


def test_duplicate_department_code(session: Session) -> None:
    departments = DepartmentRepository(session)
    departments.add(Department(code="IT", name="ІТ"))
    with pytest.raises(DuplicateDepartmentError):
        departments.add(Department(code="IT", name="Ще один"))


def test_employee_constraint_errors_are_translated(seeded: HRService) -> None:
    repository = EmployeeRepository(seeded.session)
    with pytest.raises(DuplicateEmployeeError, match="E0001"):
        repository.add(Employee(personnel_number="E0001", full_name="Дублікат", position="X",
                                salary_cents=1, department_id=1))
    seeded.session.rollback()
    with pytest.raises(DepartmentNotFoundError):
        repository.add(Employee(personnel_number="E0009", full_name="Ніхто", position="X",
                                salary_cents=1, department_id=999))


def test_get_all_with_pagination(seeded: HRService) -> None:
    repository = seeded.employees
    assert [e.personnel_number for e in repository.get_all()] == ["E0001", "E0002", "E0003"]
    assert [e.personnel_number for e in repository.get_all(limit=1, offset=1)] == ["E0002"]


def test_list_by_department(seeded: HRService) -> None:
    it = seeded.get_department("IT")
    assert [e.personnel_number for e in seeded.employees.list_by_department(it.id)] == [
        "E0001", "E0002"]
    assert seeded.employees.list_by_department(seeded.get_department("HR").id) == []


def test_search_uses_ukrainian_alphabet(seeded: HRService) -> None:
    seeded.hire("E0004", "Ірина Бондар", "Розробниця", "50000", "IT")
    names = [e.full_name for e in seeded.employees.search("розроб")]
    assert names == ["Іван Петренко", "Ірина Бондар"]
    assert uk_key("Ірина") < uk_key("Олена")  # 'І' before 'О', unlike code points of 'Я'


def test_filter_by_salary_and_position(seeded: HRService) -> None:
    repository = seeded.employees
    rich = repository.filter(min_salary_cents=5_000_000, order_by_salary=True)
    assert [e.personnel_number for e in rich] == ["E0001", "E0002"]
    assert [e.personnel_number for e in repository.filter(position="Бухгалтер")] == ["E0003"]


def test_aggregates_in_sql(seeded: HRService) -> None:
    repository = seeded.employees
    it = seeded.get_department("IT").id
    assert repository.payroll_cents() == 18_000_050
    assert repository.payroll_cents(it) == 15_000_000
    assert repository.average_cents(it) == pytest.approx(7_500_000)
    top = repository.highest_paid()
    assert top is not None and top.personnel_number == "E0001"


def test_aggregates_of_empty_department(seeded: HRService) -> None:
    empty = seeded.get_department("HR").id
    assert seeded.employees.payroll_cents(empty) == 0
    assert seeded.employees.average_cents(empty) is None
    assert seeded.employees.highest_paid(empty) is None


def test_stats_by_department_keeps_empty_departments(seeded: HRService) -> None:
    stats = {code: rest for code, *rest in seeded.employees.stats_by_department()}
    assert stats["IT"] == ["Інформаційні технології", 2, 15_000_000, 7_500_000.0, 9_000_000]
    assert stats["HR"] == ["Персонал", 0, 0, 0.0, 0]
    assert list(stats) == ["FIN", "HR", "IT"]


def test_delete(seeded: HRService) -> None:
    employee = seeded.get_employee("E0003")
    seeded.employees.delete(employee)
    assert seeded.employees.get_by_number("E0003") is None
    assert seeded.employees.count() == 2
