"""Building the lazy pipeline from the stages."""

from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from employee_stream.filters import filter_by_department, filter_by_salary
from employee_stream.models import Employee
from employee_stream.parsers import clean_lines, parse_csv_rows, validate_employees
from employee_stream.readers import read_lines, read_many
from employee_stream.transformations import normalize

T = TypeVar("T")


def count_stage(name: str, items: Iterable[T], stats: Counter[str]) -> Iterator[T]:
    """Logging of a pipeline stage: counts the elements that pass through it."""
    for item in items:
        stats[name] += 1
        yield item


def build_pipeline(
    *paths: Path,
    department: str | None = None,
    min_salary: float | None = None,
    max_salary: float | None = None,
    stats: Counter[str] | None = None,
) -> Iterator[Employee]:
    """CSV -> lines -> clean -> rows -> valid -> normalize -> [department]
    -> [salary level]. Nothing is read until the consumer asks."""
    stats = stats if stats is not None else Counter()
    lines = read_lines(paths[0]) if len(paths) == 1 else read_many(*paths)
    rows = count_stage("rows", parse_csv_rows(clean_lines(lines)), stats)
    employees: Iterator[Employee] = normalize(
        count_stage("valid", validate_employees(rows, stats), stats))
    if department:
        employees = filter_by_department(employees, department)
    if min_salary is not None or max_salary is not None:
        employees = filter_by_salary(employees, min_salary or 0.0,
                                     max_salary if max_salary is not None else float("inf"))
    return count_stage("output", employees, stats)
