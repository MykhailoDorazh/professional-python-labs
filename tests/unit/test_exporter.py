import json
from pathlib import Path

import pytest

from employee_app import exporter
from employee_app.exceptions import DataExportError
from employee_app.exporter import AtomicWriter, FileReportPublisher, export_employees_json
from employee_app.models import Employee


def test_export_employees_json(tmp_path: Path, employee: Employee) -> None:
    employee.department = "IT"
    output = tmp_path / "out" / "employees.json"
    assert export_employees_json([employee], output) == 1
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == [{"employee_id": "E0001", "name": "Іван Петренко", "position": "Розробник",
                     "role": "employee", "department": "IT", "salary": 50000.0,
                     "currency": "UAH"}]


def test_export_empty_list(tmp_path: Path) -> None:
    output = tmp_path / "employees.json"
    assert export_employees_json([], output) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == []


def test_failed_export_keeps_old_output(tmp_path: Path, employee: Employee,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "employees.json"
    output.write_text("old valid data", encoding="utf-8")

    def broken_dump(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(exporter.json, "dump", broken_dump)  # failure injection
    with pytest.raises(DataExportError) as exc_info:
        export_employees_json([employee], output)
    assert isinstance(exc_info.value.__cause__, OSError)
    assert output.read_text(encoding="utf-8") == "old valid data"
    assert not output.with_suffix(".json.tmp").exists()


def test_atomic_writer_cleanup_on_exception(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    writer = AtomicWriter(target)
    with pytest.raises(RuntimeError):
        with writer as file:
            file.write("partial")
            assert writer.temporary.exists()
            raise RuntimeError("boom")
    assert not writer.temporary.exists() and not target.exists()


def test_atomic_writer_success(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    with AtomicWriter(target) as file:
        file.write("complete")
    assert target.read_text(encoding="utf-8") == "complete"


def test_file_report_publisher(tmp_path: Path) -> None:
    FileReportPublisher(tmp_path / "reports").publish("payroll_2026-11", "Відомість")
    assert (tmp_path / "reports" / "payroll_2026-11.txt").read_text(encoding="utf-8") \
        == "Відомість\n"


def test_file_report_publisher_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_open(*args: object, **kwargs: object) -> None:
        raise PermissionError("read-only")

    monkeypatch.setattr(Path, "open", broken_open)
    with pytest.raises(DataExportError) as exc_info:
        FileReportPublisher(tmp_path).publish("report", "text")
    assert isinstance(exc_info.value.__cause__, PermissionError)
