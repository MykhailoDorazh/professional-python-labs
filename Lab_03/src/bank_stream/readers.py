"""Data sources: streaming file readers and an own iterator class."""

from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from typing import TextIO


def read_lines(path: Path) -> Iterator[str]:
    """Generator: yields lines one by one, the file is never read entirely."""
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from file


def read_many(*paths: Path) -> Iterator[str]:
    """Several files as one stream (itertools.chain). Header lines of the
    second and next files are skipped so that the CSV stays valid."""
    first, *rest = paths
    return chain(
        read_lines(first),
        *(skip_header(read_lines(path)) for path in rest),
    )


def skip_header(lines: Iterator[str]) -> Iterator[str]:
    next(lines, None)
    yield from lines


class RecordFile:
    """Iterable container: every iter() creates a new independent iterator."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __iter__(self) -> "RecordFileIterator":
        return RecordFileIterator(self.path)


class RecordFileIterator:
    """Own iterator: implements __iter__/__next__, reads one line per call."""

    def __init__(self, path: Path) -> None:
        self._file: TextIO | None = path.open("r", encoding="utf-8", newline="")
        self.line_number = 0

    def __iter__(self) -> "RecordFileIterator":
        return self

    def __next__(self) -> str:
        if self._file is None:
            raise StopIteration
        line = self._file.readline()
        if not line:
            self._file.close()
            self._file = None
            raise StopIteration
        self.line_number += 1
        return line
