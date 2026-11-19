"""Service layer: CRUD, search by department, salary aggregates, transfers, rollback."""

from datetime import date
from decimal import Decimal

import pytest

from employee_db.exceptions import (
    DepartmentNotEmptyError,
    DepartmentNotFoundError,
    DuplicateDepartmentError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
    HRError,
    InvalidSalaryError,
)
from employee_db.money import fmt, from_cents, to_cents
from employee_db.services import HRService


# ---------- money ----------
@pytest.mark.parametrize(("amount", "cents"), [("0", 0), ("0.01", 1), ("52000", 5_200_000),
                                               (Decimal("36800.50"), 3_680_050), (7, 700)])
def test_to_cents(amount: Decimal | str | int, cents: int) -> None:
    assert to_cents(amount) == cents


@pytest.mark.parametrize("amount", ["-0.01", "abc", "1.001", "NaN"])
def test_to_cents_rejects(amount: str) -> None:
    with pytest.raises(InvalidSalaryError):
        to_cents(amount)


def test_money_formatting() -> None:
    assert from_cents(3_680_050) == Decimal("36800.50")
    assert fmt(12_345_678) == "123 456.78"


# ---------- CRUD ----------
def test_create_and_read(seeded: HRService) -> None:
    employee = seeded.get_employee("e0001")
    assert (employee.full_name, employee.position, employee.salary_cents) == (
        "Олена Коваль", "Тімлід", 9_000_000)
    assert employee.department.code == "IT"
    assert employee.hire_date == date(2021, 3, 1)
    assert [e.personnel_number for e in seeded.list_employees()] == ["E0001", "E0002", "E0003"]


@pytest.mark.parametrize(
    ("number", "name", "position", "salary", "department", "error"),
    [
        ("E1", "Олег", "Аналітик", "1", "IT", HRError),
        ("E0009", "  ", "Аналітик", "1", "IT", HRError),
        ("E0009", "Олег", "", "1", "IT", HRError),
        ("E0009", "Олег", "Аналітик", "-1", "IT", InvalidSalaryError),
        ("E0009", "Олег", "Аналітик", "1000000.01", "IT", InvalidSalaryError),
        ("E0009", "Олег", "Аналітик", "1", "SALES", DepartmentNotFoundError),
        ("E0001", "Олег", "Аналітик", "1", "IT", DuplicateEmployeeError),
    ],
)
def test_hire_validation(seeded: HRService, number: str, name: str, position: str,
                         salary: str, department: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        seeded.hire(number, name, position, salary, department)
    assert seeded.employees.count() == 3  # nothing was saved


def test_salary_boundaries(seeded: HRService) -> None:
    assert seeded.hire("E0010", "Стажер", "Стажер", "0", "HR").salary_cents == 0
    assert seeded.change_salary("E0010", "1000000").salary_cents == 100_000_000


def test_update_position_and_salary(seeded: HRService) -> None:
    seeded.change_position("E0002", "Старший розробник")
    seeded.change_salary("E0002", "65000.75")
    seeded.session.expire_all()  # read again from the database
    employee = seeded.get_employee("E0002")
    assert (employee.position, employee.salary_cents) == ("Старший розробник", 6_500_075)
    with pytest.raises(HRError):
        seeded.change_position("E0002", " ")
    with pytest.raises(EmployeeNotFoundError):
        seeded.change_salary("E9999", "1")


def test_fire(seeded: HRService) -> None:
    seeded.fire("E0003")
    with pytest.raises(EmployeeNotFoundError):
        seeded.get_employee("E0003")


def test_departments_crud(seeded: HRService) -> None:
    seeded.rename_department("HR", "Відділ кадрів")
    assert seeded.get_department("hr").name == "Відділ кадрів"
    with pytest.raises(DuplicateDepartmentError):
        seeded.create_department("IT", "Ще один IT")
    with pytest.raises(HRError):
        seeded.create_department(" ", "Без коду")
    seeded.delete_department("HR")  # empty -> allowed
    with pytest.raises(DepartmentNotFoundError):
        seeded.get_department("HR")


def test_department_with_employees_cannot_be_deleted(seeded: HRService) -> None:
    with pytest.raises(DepartmentNotEmptyError) as exc_info:
        seeded.delete_department("IT")
    assert "FOREIGN KEY" in str(exc_info.value.__cause__)
    assert len(seeded.employees_in("IT")) == 2  # rolled back


# ---------- search and aggregates ----------
def test_search_by_department(seeded: HRService) -> None:
    assert [e.personnel_number for e in seeded.employees_in("it")] == ["E0001", "E0002"]
    assert [e.personnel_number for e in seeded.employees_in("FIN")] == ["E0003"]
    assert seeded.employees_in("HR") == []
    with pytest.raises(DepartmentNotFoundError):
        seeded.employees_in("SALES")


def test_salary_aggregates(seeded: HRService) -> None:
    assert seeded.payroll() == Decimal("180000.50")
    assert seeded.average_salary() == Decimal("60000.17")
    assert seeded.payroll("IT") == Decimal("150000.00")
    assert seeded.average_salary("IT") == Decimal("75000.00")
    top = seeded.highest_paid()
    assert top is not None and top.personnel_number == "E0001"
    fin_top = seeded.highest_paid("FIN")
    assert fin_top is not None and fin_top.personnel_number == "E0003"


def test_aggregates_of_empty_department(seeded: HRService) -> None:
    assert seeded.payroll("HR") == Decimal("0.00")
    assert seeded.average_salary("HR") == Decimal("0.00")
    assert seeded.highest_paid("HR") is None


def test_department_stats(seeded: HRService) -> None:
    stats = {code: rest for code, *rest in seeded.department_stats()}
    assert stats["IT"] == ["Інформаційні технології", 2, Decimal("150000.00"),
                           Decimal("75000.00"), Decimal("90000.00")]
    assert stats["HR"][1] == 0


# ---------- transfers and transactions ----------
def test_transfer_between_departments(seeded: HRService) -> None:
    seeded.transfer("E0002", "FIN")
    assert [e.personnel_number for e in seeded.employees_in("FIN")] == ["E0002", "E0003"]
    assert [e.personnel_number for e in seeded.employees_in("IT")] == ["E0001"]
    with pytest.raises(DepartmentNotFoundError):
        seeded.transfer("E0002", "SALES")
    assert seeded.get_employee("E0002").department.code == "FIN"


def test_mass_transfer_commit(seeded: HRService) -> None:
    assert seeded.transfer_many(["E0001", "E0002"], "HR") == 2
    seeded.session.expire_all()
    assert [e.personnel_number for e in seeded.employees_in("HR")] == ["E0001", "E0002"]
    assert seeded.employees_in("IT") == []


def test_mass_transfer_rollback(seeded: HRService) -> None:
    """E0001 is moved first, then E9999 fails -> the whole transaction is rolled back."""
    with pytest.raises(EmployeeNotFoundError):
        seeded.transfer_many(["E0001", "E9999"], "HR")
    seeded.session.expire_all()
    assert seeded.get_employee("E0001").department.code == "IT"
    assert seeded.employees_in("HR") == []


def test_mass_raise_commit(seeded: HRService) -> None:
    assert seeded.raise_salaries("IT", "10") == 2
    seeded.session.expire_all()
    assert seeded.payroll("IT") == Decimal("165000.00")
    assert seeded.payroll("FIN") == Decimal("30000.50")  # other departments untouched


def test_mass_raise_rollback(seeded: HRService) -> None:
    """E0002 gets +1100 % first (720 000 - OK), E0001 would get 1 080 000 -> ROLLBACK."""
    with pytest.raises(InvalidSalaryError, match="E0001") as exc_info:
        seeded.raise_salaries("IT", "1100")
    assert "CHECK constraint failed" in str(exc_info.value.__cause__)
    seeded.session.expire_all()
    assert seeded.get_employee("E0002").salary_cents == 6_000_000
    assert seeded.payroll("IT") == Decimal("150000.00")


def test_mass_raise_invalid_percent(seeded: HRService) -> None:
    with pytest.raises(InvalidSalaryError):
        seeded.raise_salaries("IT", "-100")


def test_session_is_usable_after_rollback(seeded: HRService) -> None:
    with pytest.raises(InvalidSalaryError):
        seeded.raise_salaries("IT", "1100")
    seeded.hire("E0004", "Ірина Бондар", "Аналітик", "40000", "FIN")
    assert seeded.employees.count() == 4
