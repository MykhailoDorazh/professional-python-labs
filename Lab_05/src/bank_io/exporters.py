"""Serialization with atomic output."""

import csv
import json
import logging
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import TextIO

from bank_io.exceptions import DataExportError
from bank_io.models import Operation

logger = logging.getLogger(__name__)


class AtomicWriter:
    """Context manager: writes into <name>.tmp and replaces the target only
    when the block finished without errors. On error the temporary file is
    deleted, so the previous valid output stays untouched."""

    def __init__(self, path: Path, *, newline: str | None = None) -> None:
        self.path = path
        self.temporary = path.with_suffix(path.suffix + ".tmp")
        self._newline = newline
        self._file: TextIO | None = None

    def __enter__(self) -> TextIO:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.temporary.open("w", encoding="utf-8", newline=self._newline)
        except OSError as error:
            raise DataExportError(f"Cannot open {self.temporary}") from error
        return self._file

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 traceback: TracebackType | None) -> bool:
        if self._file is not None:
            self._file.close()
        if exc_type is not None:
            self.temporary.unlink(missing_ok=True)
            logger.error("Export to %s aborted, temporary file removed", self.path.name)
            return False  # exception propagates
        try:
            self.temporary.replace(self.path)
        except OSError as error:
            self.temporary.unlink(missing_ok=True)
            raise DataExportError(f"Cannot replace {self.path}") from error
        return False


def export_json(operations: Iterable[Operation], path: Path) -> int:
    """Streaming JSON array export: records are written one by one."""
    count = 0
    try:
        with AtomicWriter(path) as file:
            file.write("[")
            for operation in operations:
                file.write(",\n  " if count else "\n  ")
                json.dump(operation.to_dict(), file, ensure_ascii=False)
                count += 1
            file.write("\n]\n")
    except (OSError, TypeError) as error:
        raise DataExportError(f"Cannot export data to {path}") from error
    return count


def export_errors_csv(errors: Iterable[tuple[int, str, str]], path: Path) -> None:
    """Separate error report (no confidential data, only line/field/message)."""
    with AtomicWriter(path, newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["line", "field", "error"])
        writer.writerows(errors)


def export_summary(summary: dict[str, object], path: Path) -> None:
    with AtomicWriter(path) as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
