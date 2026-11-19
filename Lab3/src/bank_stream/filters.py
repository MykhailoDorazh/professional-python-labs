"""Lazy filtering and search."""

from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

from bank_stream.models import Operation, ProcessedOperation

T = TypeVar("T")


def filter_by_client(operations: Iterable[Operation], text: str) -> Iterator[Operation]:
    """Keep operations of clients whose name contains `text`."""
    needle = text.lower()
    for operation in operations:
        if needle in operation.client.lower():
            yield operation


def filter_by_balance(
    records: Iterable[ProcessedOperation],
    minimum: float = 0.0,
    maximum: float = float("inf"),
) -> Iterator[ProcessedOperation]:
    """Keep accounts whose balance after the operation is in [minimum, maximum]."""
    for record in records:
        if minimum <= record.balance_after <= maximum:
            yield record


def find_first(records: Iterable[T], predicate: Callable[[T], bool]) -> T | None:
    """Lazy search with early termination: stops at the first match."""
    for record in records:
        if predicate(record):
            return record
    return None


def find_account(records: Iterable[T], account_number: str) -> T | None:
    """Search by account_number (stops reading the file when found)."""
    number = account_number.upper()
    return find_first(records, lambda r: r.account_number == number)
