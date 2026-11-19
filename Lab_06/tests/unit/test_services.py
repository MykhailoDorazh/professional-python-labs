from collections.abc import Callable
from unittest.mock import Mock

import pytest

from employee_app.exceptions import (
    DepartmentNotFoundError,
    DuplicateEmployeeError,
    EmployeeNotFoundError,
)
from employee_app.models import Department, Employee
from employee_app.protocols import EmployeeStore
from employee_app.repositories import InMemoryRepository
from employee_app.services import ConsoleNotifier, HRService, PayrollService
from employee_app.value_objects import Money


def test_add_employee_assigns_department_and_notifies(
        employees: InMemoryRepository[Employee], departments: InMemoryRepository[Department],
        notifier: Mock, employee: Employee) -> None:
    HRService(employees, departments, notifier).add_employee(employee, "it")
    assert "E0001" in employees
    assert employee.department == "IT" and employee in departments["IT"]
    notifier.send.assert_called_once_with(
        "E0001", "зараховано до відділу «Інформаційні технології»")


def test_unknown_department_rejected_before_saving(
        hr: HRService, employees: InMemoryRepository[Employee],
        employee_factory: Callable[..., Employee], notifier: Mock) -> None:
    with pytest.raises(DepartmentNotFoundError, match="LOG"):
        hr.add_employee(employee_factory("E0009"), "LOG")
    assert "E0009" not in employees
    notifier.send.assert_not_called()


def test_duplicate_employee_rejected(hr: HRService,
                                     employee_factory: Callable[..., Employee]) -> None:
    with pytest.raises(DuplicateEmployeeError):
        hr.add_employee(employee_factory("E0001", name="Дублікат"), "FIN")


def test_find_employee(hr: HRService) -> None:
    assert hr.find_employee("e0001").employee_id == "E0001"
    with pytest.raises(EmployeeNotFoundError, match="E9999"):
        hr.find_employee("E9999")


def test_search_by_department(staffed: HRService) -> None:
    assert [e.employee_id for e in staffed.find_by_department("IT")] == ["E0001", "E0002"]
    assert [e.employee_id for e in staffed.find_by_department("fin")] == ["E0003"]
    assert staffed.find_by_department("HR") == []  # порожній відділ
    with pytest.raises(DepartmentNotFoundError):
        staffed.find_by_department("SALES")


def test_change_salary_does_not_disclose_amount(hr: HRService, notifier: Mock) -> None:
    hr.change_salary("E0001", Money(55_555))
    assert hr.find_employee("E0001").salary == Money(55_555)
    notifier.send.assert_called_once_with("E0001", "оклад змінено")


def test_transfer_between_departments(staffed: HRService, notifier: Mock) -> None:
    staffed.transfer("E0001", "HR")
    assert [e.employee_id for e in staffed.find_by_department("HR")] == ["E0001"]
    assert [e.employee_id for e in staffed.find_by_department("IT")] == ["E0002"]
    notifier.send.assert_called_with("E0001", "переведено до відділу «Персонал»")


def test_transfer_of_employee_without_department(hr: HRService) -> None:
    employee = hr.find_employee("E0001")
    hr.department("IT").remove(employee)  # працівник тимчасово поза відділами
    hr.transfer("E0001", "FIN")
    assert employee.department == "FIN"
    assert hr.find_by_department("IT") == []


def test_notifier_failure_does_not_cancel_operation(hr: HRService, notifier: Mock) -> None:
    notifier.send.side_effect = ConnectionError("SMTP unavailable")
    hr.change_salary("E0001", Money(60_000))
    assert hr.find_employee("E0001").salary == Money(60_000)  # операцію виконано
    assert hr.failed_notifications == 1


def test_service_with_repository_mock(employee: Employee, departments: InMemoryRepository[Department],
                                      notifier: Mock) -> None:
    repository = Mock(spec=EmployeeStore)
    repository.get.return_value = employee
    hr = HRService(repository, departments, notifier)
    assert hr.find_employee("E0001") is employee
    repository.get.assert_called_once_with("E0001")
    repository.get.return_value = None
    with pytest.raises(EmployeeNotFoundError):
        hr.find_employee("E0002")
    repository.add.assert_not_called()


def test_salary_statistics(staffed: HRService, payroll: PayrollService) -> None:
    assert payroll.total_payroll() == Money(170_000.5)
    assert payroll.average_salary().amount == pytest.approx(56_666.83)
    top = payroll.highest_paid()
    assert top is not None and top.employee_id == "E0002"
    it = staffed.find_by_department("IT")
    assert payroll.average_salary(it) == Money(70_000)
    assert payroll.total_payroll(it) == Money(140_000)


def test_statistics_of_empty_department(staffed: HRService, payroll: PayrollService) -> None:
    empty = staffed.find_by_department("HR")
    assert payroll.total_payroll(empty) == Money(0)
    assert payroll.average_salary(empty) == Money(0)
    assert payroll.highest_paid(empty) is None


def test_statistics_on_empty_repository(payroll: PayrollService) -> None:
    assert payroll.total_payroll() == Money(0)
    assert payroll.average_salary() == Money(0)
    assert payroll.highest_paid() is None
    assert payroll.run_payroll("2026-11") == []
    assert payroll.by_department() == {}


def test_run_payroll_and_by_department(staffed: HRService, payroll: PayrollService) -> None:
    records = payroll.run_payroll("2026-11")
    assert [r.id for r in records] == [1, 2, 3]
    assert records[1].bonus == Money(18_000)  # manager: 20 %
    stats = payroll.by_department()
    assert stats["IT"] == {"employees": 2, "payroll": 140_000.0, "average": 70_000.0}
    assert list(stats) == ["FIN", "IT"]


def test_console_notifier_prints(capsys: pytest.CaptureFixture[str]) -> None:
    ConsoleNotifier().send("E0001", "hello")
    assert "[notify -> E0001] hello" in capsys.readouterr().out


def test_repository_collection_protocol(employees: InMemoryRepository[Employee],
                                        employee: Employee) -> None:
    employees.add(employee)
    assert employees["e0001"] is employee
    assert employees.find(lambda e: e.salary.amount > 10_000) == [employee]
    assert employees.all() == [employee] and 5 not in employees
    assert employees.remove("E0001") and not employees.remove("E0001")


def test_repository_rejects_duplicate_key(employees: InMemoryRepository[Employee],
                                          employee_factory: Callable[..., Employee]) -> None:
    employees.add(employee_factory("E0001"))
    with pytest.raises(DuplicateEmployeeError, match="E0001"):
        employees.add(employee_factory("E0001", 5))
    assert len(employees) == 1
