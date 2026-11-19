"""Transformation stage: applying deposits and withdrawals in the stream."""

from collections.abc import Iterable, Iterator

from bank_stream.models import Operation, ProcessedOperation


def apply_operation(op: Operation) -> ProcessedOperation:
    """Apply one operation. A withdrawal that would make the balance
    negative is rejected and the balance stays unchanged."""
    if op.operation == "deposit":
        after, accepted = round(op.balance + op.amount, 2), True
    elif op.amount <= op.balance:
        after, accepted = round(op.balance - op.amount, 2), True
    else:
        after, accepted = op.balance, False
    return ProcessedOperation(
        op.account_number, op.client, op.operation, op.amount,
        op.balance, after, accepted,
    )


def apply_operations(operations: Iterable[Operation]) -> Iterator[ProcessedOperation]:
    """Streaming application of operations (generator)."""
    for operation in operations:
        yield apply_operation(operation)


def normalize_clients(operations: Iterable[Operation]) -> Iterator[Operation]:
    """Bring client names to Title Case: 'іВАН петренко' -> 'Іван Петренко'."""
    for operation in operations:
        yield operation._replace(client=" ".join(operation.client.split()).title())


def short_view(records: Iterable[ProcessedOperation]) -> Iterator[str]:
    """Lazy transformation into a short text representation."""
    return (
        f"{r.account_number} {r.client:<16} {r.operation:<8} {r.amount:>9.2f}: "
        f"{r.balance_before:>9.2f} -> {r.balance_after:>9.2f}"
        f"{'' if r.accepted else '  ВІДХИЛЕНО'}"
        for r in records
    )
