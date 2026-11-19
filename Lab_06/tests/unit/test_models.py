from collections.abc import Callable

import pytest

from employee_app.exceptions import InvalidEmployeeError, InvalidSalaryError
from employee_app.models import Department, Developer, Employee, Manager
from employee_app.value_objects import Money


def test_employee_creation(employee: Employee) -> None:
    assert employee.employee_id == "E0001"
    assert employee.name == "Іван Петренко"
    assert employee.salary == Money(50_000)
    assert employee.role == "employee"
    assert employee.department is None


def test_name_is_normalized(employee_factory: Callable[..., Employee]) -> None:
    assert employee_factory(name="  Олена   Коваль ").name == "Олена Коваль"


@pytest.mark.parametrize(("name", "position"), [("", "Розробник"), ("   ", "Розробник"),
                                                ("Іван", "")])
def test_invalid_name_or_position(employee_factory: Callable[..., Employee],
                                  name: str, position: str) -> None:
    with pytest.raises(InvalidEmployeeError):
        employee_factory(name=name, position=position)


@pytest.mark.parametrize(
    ("salary", "valid"),
    [
        pytest.param(0, True, id="zero-boundary"),
        pytest.param(0.01, True, id="one-cent"),
        pytest.param(1_000_000, True, id="max-boundary"),
        pytest.param(1_000_000.01, False, id="over-max"),
    ],
)
def test_salary_boundaries(employee_factory: Callable[..., Employee],
                           salary: float, valid: bool) -> None:
    if valid:
        assert employee_factory(salary=salary).salary == Money(salary)
    else:
        with pytest.raises(InvalidSalaryError) as exc_info:
            employee_factory(salary=salary)
        assert exc_info.value.value == pytest.approx(salary)


def test_negative_salary_is_rejected_by_money() -> None:
    with pytest.raises(ValueError):
        Employee("E0001", "Іван", "Розробник", Money(-1))


def test_change_salary_returns_old_value(any_employee: Employee) -> None:
    old = any_employee.change_salary(Money(45_000))
    assert old == Money(40_000)
    assert any_employee.salary == Money(45_000)


def test_invalid_salary_change_keeps_state(any_employee: Employee) -> None:
    with pytest.raises(InvalidSalaryError):
        any_employee.change_salary(Money(2_000_000))
    assert any_employee.salary == Money(40_000)  # стан не змінився


@pytest.mark.parametrize(("percent", "expected"), [(10, 44_000), (0.5, 40_200)])
def test_raise_salary(any_employee: Employee, percent: float, expected: float) -> None:
    assert any_employee.raise_salary(percent) == Money(expected)


@pytest.mark.parametrize("percent", [0, -5])
def test_raise_must_be_positive(employee: Employee, percent: float) -> None:
    with pytest.raises(InvalidSalaryError):
        employee.raise_salary(percent)


def test_polymorphic_bonus(employee_factory: Callable[..., Employee]) -> None:
    plain = employee_factory(salary=10_000)
    senior = employee_factory("E0002", 10_000, "developer", level="senior")
    junior = employee_factory("E0003", 10_000, "developer", level="junior")
    lead = employee_factory("E0004", 10_000, "manager", bonus_rate=0.1)
    assert isinstance(lead, Manager) and isinstance(senior, Developer)
    lead.add_to_team(senior)
    lead.add_to_team(senior)  # duplicate is ignored
    lead.add_to_team(lead)  # manager is not in his own team
    assert [e.bonus().amount for e in (plain, senior, junior, lead)] == [0, 1_500, 500, 1_500]


@pytest.mark.parametrize("rate", [-0.1, 0.51])
def test_invalid_manager_bonus_rate(employee_factory: Callable[..., Employee],
                                    rate: float) -> None:
    with pytest.raises(InvalidSalaryError):
        employee_factory(role="manager", bonus_rate=rate)


def test_payroll_record(employee_factory: Callable[..., Employee]) -> None:
    record = employee_factory(salary=20_000, role="developer").payroll(7, "2026-11")
    assert (record.id, record.period, record.employee_id) == (7, "2026-11", "E0001")
    assert record.total == Money(22_000)
    assert str(record).startswith("#7 2026-11 E0001")


def test_department_collection(employee_factory: Callable[..., Employee]) -> None:
    department = Department(" it ", "Інформаційні технології")
    first, second = employee_factory("E0001", 100), employee_factory("E0002", 200)
    department.add(first)
    department.add(second)
    assert department.code == "IT" and len(department) == 2
    assert first in department and first.department == "IT"
    assert department.payroll() == Money(300)
    department.remove(first)
    assert first not in department and first.department is None
    assert "IT" in str(department)


def test_empty_department() -> None:
    department = Department("HR", "Персонал")
    assert len(department) == 0
    assert list(department) == []
    assert department.payroll() == Money(0)
    with pytest.raises(InvalidEmployeeError):
        Department("", "Без коду")


def test_dunder_methods(employee_factory: Callable[..., Employee]) -> None:
    poor, rich = employee_factory("E0001", 10), employee_factory("E0002", 900)
    assert poor < rich and max([poor, rich]) is rich
    assert poor == employee_factory("E0001", 999) and poor != "E0001"
    assert len({poor, rich}) == 2
    assert "E0002" in repr(rich) and "[employee]" in str(rich)
