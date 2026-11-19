from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from employee_app.config import AppConfig
from employee_app.exceptions import DataImportError, RecordValidationError
from employee_app.importer import ImportStatistics, parse_employee, read_employees
from employee_app.models import Developer, Manager

HEADER = "employee_id,name,position,department,salary,role\n"
EMPLOYEES = (HEADER
             + "E0001,Олена Коваль,Тімлід,IT,90000,manager\n"
             + "E0002,Іван Петренко,Розробник,it,52000.50,developer\n"
             + "E0003,Марія Бондар,HR-менеджер,HR,30000,\n")


def test_import_employees(write_file: Callable[[str, str], Path], config: AppConfig) -> None:
    records = list(read_employees(write_file("employees.csv", EMPLOYEES), config,
                                  ImportStatistics()))
    assert [r.employee.employee_id for r in records] == ["E0001", "E0002", "E0003"]
    assert [r.department for r in records] == ["IT", "IT", "HR"]
    assert isinstance(records[0].employee, Manager)
    assert isinstance(records[1].employee, Developer)
    assert records[2].employee.role == "employee"  # empty role -> default
    assert records[1].employee.salary.amount == pytest.approx(52_000.5)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        pytest.param("E0001,Іван,Розробник,IT,abc,employee", "salary", id="bad-salary"),
        pytest.param("E0001,Іван,Розробник,IT,-100,employee", "salary", id="negative-salary"),
        pytest.param("E0001,Іван,Розробник,IT,7999.99,employee", "salary", id="below-min"),
        pytest.param("E0001,Іван,Розробник,IT,1000000.01,employee", "salary", id="above-max"),
        pytest.param("E0001,Іван,Розробник,LOG,9000,employee", "department", id="bad-department"),
        pytest.param("E0001,Іван,Розробник,IT,9000,intern", "role", id="bad-role"),
        pytest.param("E1,Іван,Розробник,IT,9000,employee", None, id="bad-id"),
        pytest.param("E0001,,Розробник,IT,9000,employee", None, id="empty-name"),
    ],
)
def test_malformed_employee_record(config: AppConfig, row: str, field: str | None) -> None:
    keys = HEADER.strip().split(",")
    with pytest.raises(RecordValidationError) as exc_info:
        parse_employee(dict(zip(keys, row.split(","), strict=True)), 2, config)
    assert exc_info.value.line_number == 2
    assert exc_info.value.field == field


def test_malformed_salary_is_chained(config: AppConfig) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        parse_employee({"employee_id": "E0001", "name": "Іван", "position": "Розробник",
                        "department": "IT", "salary": "5O000"}, 5, config)
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("salary", "valid"),
    [("7999.99", False), ("8000", True), ("8000.01", True), ("1000000", True),
     ("1000000.01", False)],
)
def test_min_salary_boundaries(config: AppConfig, salary: str, valid: bool) -> None:
    row = {"employee_id": "e0001", "name": "Іван", "position": "Розробник",
           "department": "fin", "salary": salary}
    if valid:
        record = parse_employee(row, 2, config)
        assert record.employee.employee_id == "E0001" and record.department == "FIN"
    else:
        with pytest.raises(RecordValidationError, match="range"):
            parse_employee(row, 2, config)


def test_min_salary_comes_from_configuration(config: AppConfig) -> None:
    row = {"employee_id": "E0001", "name": "Іван", "position": "Стажер", "department": "IT",
           "salary": "5000"}
    with pytest.raises(RecordValidationError):
        parse_employee(row, 2, config)
    assert parse_employee(row, 2, replace(config, min_salary=0)).employee.salary.amount == 5_000


MIXED = (HEADER + "E0001,Іван,Розробник,IT,9000,employee\nE0002,Олена,Тімлід,LOG,9000,\n"
         "E0003,Андрій,Бухгалтер,FIN,x,\nE0004,Марія,HR,HR,9500,\n")


def test_tolerant_mode_skips_invalid(write_file: Callable[[str, str], Path],
                                     config: AppConfig) -> None:
    stats = ImportStatistics()
    records = list(read_employees(write_file("e.csv", MIXED), config, stats))
    assert [r.line_number for r in records] == [2, 5]
    assert (stats.total, stats.valid, stats.invalid) == (4, 2, 2)
    assert stats.errors[0].startswith("line 3")


def test_strict_mode_stops_at_first_error(write_file: Callable[[str, str], Path],
                                          config: AppConfig) -> None:
    stats = ImportStatistics()
    with pytest.raises(RecordValidationError, match="LOG"):
        list(read_employees(write_file("e.csv", MIXED), replace(config, skip_invalid=False),
                            stats))
    assert (stats.valid, stats.invalid) == (1, 1)


def test_missing_input_file(tmp_path: Path, config: AppConfig) -> None:
    with pytest.raises(DataImportError) as exc_info:
        list(read_employees(tmp_path / "absent.csv", config, ImportStatistics()))
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)
