"""Batch processing and batch export."""

import csv
from collections.abc import Iterable, Iterator
from itertools import groupby, islice
from pathlib import Path
from typing import TypeVar

from employee_stream.models import Employee

T = TypeVar("T")
HEADER = ["employee_id", "name", "position", "department", "salary"]


def batched(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Split a stream into lists of `size` elements (islice).
    Only the current batch is kept in memory."""
    if size < 1:
        raise ValueError("size must be >= 1")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def summarize_batch(batch: list[Employee]) -> dict[str, float]:
    """Payroll of one batch grouped by department with itertools.groupby
    (the batch is sorted by the same key first)."""
    by_department = sorted(batch, key=lambda e: e.department)
    summary: dict[str, float] = {"size": len(batch)}
    for department, group in groupby(by_department, key=lambda e: e.department):
        summary[department] = round(sum(e.salary for e in group), 2)
    summary["payroll"] = round(sum(e.salary for e in batch), 2)
    return summary


def export_batches(employees: Iterable[Employee], folder: Path, size: int,
                   prefix: str = "employees") -> Iterator[Path]:
    """Batch export: every `size` records go to a separate CSV file.
    Files are written one by one while the stream is being read."""
    folder.mkdir(parents=True, exist_ok=True)
    for number, batch in enumerate(batched(employees, size), 1):
        path = folder / f"{prefix}_{number:03d}.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            writer.writerows(batch)
        yield path
