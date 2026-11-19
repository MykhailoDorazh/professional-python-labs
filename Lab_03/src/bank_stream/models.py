"""Records that travel through the pipeline (immutable NamedTuples)."""

from typing import NamedTuple

ACCOUNT_NUMBER_PATTERN = r"UA\d{8}"
OPERATIONS: tuple[str, ...] = ("deposit", "withdraw")


class Operation(NamedTuple):
    """Validated input record: account and the operation to apply."""

    account_number: str
    client: str
    balance: float
    operation: str
    amount: float


class ProcessedOperation(NamedTuple):
    """Result of applying an operation to the account."""

    account_number: str
    client: str
    operation: str
    amount: float
    balance_before: float
    balance_after: float
    accepted: bool
