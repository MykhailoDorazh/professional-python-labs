"""Building the lazy pipeline from the stages."""

from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from bank_stream.filters import filter_by_balance, filter_by_client
from bank_stream.models import ProcessedOperation
from bank_stream.parsers import clean_lines, parse_csv_rows, validate_operations
from bank_stream.readers import read_lines, read_many
from bank_stream.transformations import apply_operations, normalize_clients

T = TypeVar("T")


def count_stage(name: str, items: Iterable[T], stats: Counter[str]) -> Iterator[T]:
    """Logging of a pipeline stage: counts the elements that pass through it."""
    for item in items:
        stats[name] += 1
        yield item


def build_pipeline(
    *paths: Path,
    client: str | None = None,
    min_balance: float | None = None,
    stats: Counter[str] | None = None,
) -> Iterator[ProcessedOperation]:
    """CSV -> lines -> clean -> rows -> valid -> [client] -> normalize
    -> apply -> [balance filter]. Nothing is read until the consumer asks."""
    stats = stats if stats is not None else Counter()
    lines = read_lines(paths[0]) if len(paths) == 1 else read_many(*paths)
    rows = count_stage("rows", parse_csv_rows(clean_lines(lines)), stats)
    valid = count_stage("valid", validate_operations(rows, stats), stats)
    if client:
        valid = filter_by_client(valid, client)
    processed = apply_operations(normalize_clients(valid))
    if min_balance is not None:
        processed = filter_by_balance(processed, min_balance)
    return count_stage("output", processed, stats)
