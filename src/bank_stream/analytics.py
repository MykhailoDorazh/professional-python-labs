"""Aggregation stage: one pass, O(1) memory regardless of the data size."""

from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import accumulate
from typing import Any

from bank_stream.models import ProcessedOperation


def calculate_statistics(records: Iterable[ProcessedOperation]) -> dict[str, Any]:
    """Count, total funds, average, min/max balance, accepted/rejected."""
    count = 0
    total = 0.0
    richest: ProcessedOperation | None = None
    poorest: ProcessedOperation | None = None
    kinds: Counter[str] = Counter()
    for record in records:
        count += 1
        total += record.balance_after
        kinds[record.operation if record.accepted else "rejected"] += 1
        if richest is None or record.balance_after > richest.balance_after:
            richest = record
        if poorest is None or record.balance_after < poorest.balance_after:
            poorest = record
    return {
        "count": count,
        "total_funds": round(total, 2),
        "average": round(total / count, 2) if count else 0.0,
        "richest": richest,
        "poorest": poorest,
        "operations": dict(kinds),
    }


def streaming_total(records: Iterable[ProcessedOperation]) -> float:
    """Total funds via a generator expression (no intermediate list)."""
    return round(sum(record.balance_after for record in records), 2)


def running_totals(records: Iterable[ProcessedOperation]) -> Iterator[float]:
    """Cumulative total of funds after each record (itertools.accumulate)."""
    return accumulate(record.balance_after for record in records)


def streaming_average(values: Iterable[float]) -> float:
    total, count = 0.0, 0
    for value in values:
        total += value
        count += 1
    return total / count if count else 0.0
