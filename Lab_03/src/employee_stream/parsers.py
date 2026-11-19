"""Cleaning, parsing and streaming validation stages."""

import csv
import re
from collections import Counter
from collections.abc import Iterable, Iterator

from employee_stream.models import EMPLOYEE_ID_PATTERN, MAX_SALARY, Employee

_ID_RE = re.compile(EMPLOYEE_ID_PATTERN)


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Skip empty lines and comments (#...)."""
    for line in lines:
        value = line.strip()
        if value and not value.startswith("#"):
            yield value + "\n"


def parse_csv_rows(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    """CSV lines -> dicts. csv.DictReader is lazy itself."""
    yield from csv.DictReader(lines)


def validate_employees(
    rows: Iterable[dict[str, str]],
    stats: Counter[str] | None = None,
) -> Iterator[Employee]:
    """Streaming validation: id, name, position, department, 0 <= salary <= limit.

    Invalid records are skipped one by one (nothing is collected in memory);
    the reasons are counted in `stats`.
    """
    for row in rows:
        reason = None
        try:
            employee_id = (row["employee_id"] or "").strip().upper()
            name = (row["name"] or "").strip()
            position = (row["position"] or "").strip()
            department = (row["department"] or "").strip()
            salary = float(row["salary"])
        except (KeyError, TypeError, ValueError):
            reason = "invalid:format"
        else:
            if not _ID_RE.fullmatch(employee_id):
                reason = "invalid:employee_id"
            elif not name:
                reason = "invalid:name"
            elif not position:
                reason = "invalid:position"
            elif not department:
                reason = "invalid:department"
            elif not 0 <= salary <= MAX_SALARY:
                reason = "invalid:salary"

        if reason:
            if stats is not None:
                stats[reason] += 1
            continue
        yield Employee(employee_id, name, position, department, salary)
