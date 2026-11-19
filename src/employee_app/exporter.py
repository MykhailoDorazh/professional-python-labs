"""Atomic JSON/text export."""

import json
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import TextIO

from employee_app.exceptions import DataExportError
from employee_app.models import Employee


class AtomicWriter:
    """Writes into <name>.tmp and replaces the target only on success."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.temporary = path.with_suffix(path.suffix + ".tmp")
        self._file: TextIO | None = None

    def __enter__(self) -> TextIO:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.temporary.open("w", encoding="utf-8")
        return self._file

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 traceback: TracebackType | None) -> bool:
        assert self._file is not None
        self._file.close()
        if exc_type is not None:
            self.temporary.unlink(missing_ok=True)
            return False
        self.temporary.replace(self.path)
        return False


def employee_to_dict(employee: Employee) -> dict[str, object]:
    return {"employee_id": employee.employee_id, "name": employee.name,
            "position": employee.position, "role": employee.role,
            "department": employee.department, "salary": employee.salary.amount,
            "currency": employee.salary.currency}


def export_employees_json(employees: Iterable[Employee], path: Path) -> int:
    try:
        with AtomicWriter(path) as file:
            data = [employee_to_dict(employee) for employee in employees]
            json.dump(data, file, ensure_ascii=False, indent=2)
    except (OSError, TypeError) as error:
        raise DataExportError(f"Cannot export employees to {path}") from error
    return len(data)


class FileReportPublisher:
    """ReportPublisher that writes reports into a folder (atomically)."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def publish(self, name: str, content: str) -> None:
        try:
            with AtomicWriter(self.folder / f"{name}.txt") as file:
                file.write(content + "\n")
        except OSError as error:
            raise DataExportError(f"Cannot write report {name}") from error
