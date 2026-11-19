"""Streaming readers behind one Importer protocol (CSV and JSON Lines)."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from employee_io.exceptions import DataImportError

Row = dict[str, str]
NumberedRow = tuple[int, Row]


class Importer(Protocol):
    def read(self, path: Path) -> Iterator[NumberedRow]: ...


class CsvImporter:
    """Reads a CSV file row by row: (line number, row)."""

    REQUIRED = ("employee_id", "name", "position", "department", "salary")

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                missing = set(self.REQUIRED) - set(reader.fieldnames or ())
                if missing:
                    raise DataImportError(f"CSV header misses columns: {sorted(missing)}")
                for line_number, row in enumerate(reader, start=2):
                    yield line_number, row
        except UnicodeDecodeError as error:
            raise DataImportError(f"Input file is not UTF-8: {path}") from error
        except OSError as error:
            raise DataImportError(f"Cannot read input file: {path}") from error


class JsonLinesImporter:
    """Reads JSON Lines: one JSON object per line."""

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with path.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise DataImportError(f"Invalid JSON at line {line_number}") from error
                    yield line_number, {key: str(value) for key, value in data.items()}
        except OSError as error:
            raise DataImportError(f"Cannot read input file: {path}") from error


IMPORTERS: dict[str, Importer] = {".csv": CsvImporter(), ".jsonl": JsonLinesImporter()}


def get_importer(path: Path) -> Importer:
    """Choose the importer by file extension."""
    try:
        return IMPORTERS[path.suffix.lower()]
    except KeyError as error:
        raise DataImportError(f"Unsupported input format: {path.suffix}") from error
