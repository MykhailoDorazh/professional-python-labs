"""Batch processing."""

from collections.abc import Iterable, Iterator
from itertools import groupby, islice
from typing import TypeVar

from bank_stream.models import ProcessedOperation

T = TypeVar("T")


def batched(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Split a stream into lists of `size` elements (islice).
    Only the current batch is kept in memory."""
    if size < 1:
        raise ValueError("size must be >= 1")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def summarize_batch(batch: list[ProcessedOperation]) -> dict[str, float]:
    """Totals of one batch, operations grouped with itertools.groupby
    (the batch is sorted by the same key first)."""
    by_kind = sorted(batch, key=lambda r: (r.operation, r.accepted))
    summary: dict[str, float] = {"size": len(batch)}
    for (operation, accepted), group in groupby(by_kind, key=lambda r: (r.operation, r.accepted)):
        name = operation if accepted else f"{operation}_rejected"
        summary[name] = round(sum(r.amount for r in group), 2)
    summary["funds"] = round(sum(r.balance_after for r in batch), 2)
    return summary
