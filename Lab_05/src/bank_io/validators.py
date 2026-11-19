"""Validation of one record and application of the operation."""

import re

from bank_io.exceptions import InsufficientFundsError, RecordValidationError
from bank_io.models import Operation, ProcessingConfig

ACCOUNT_RE = re.compile(r"UA\d{8}")


def _number(row: dict[str, str], field: str, line_number: int) -> float:
    try:
        return float(row[field])
    except KeyError as error:
        raise RecordValidationError(f"Missing field {field}", line_number=line_number,
                                    field=field) from error
    except (TypeError, ValueError) as error:
        raise RecordValidationError(f"{field} must be numeric", line_number=line_number,
                                    field=field) from error


def parse_operation(row: dict[str, str], *, line_number: int,
                    config: ProcessingConfig) -> Operation:
    """Validate a raw row and apply the operation. Raises RecordValidationError."""
    number = (row.get("account_number") or "").strip().upper()
    if not ACCOUNT_RE.fullmatch(number):
        raise RecordValidationError("Invalid account number", line_number=line_number,
                                    field="account_number")
    client = (row.get("client") or "").strip()
    if not client:
        raise RecordValidationError("Client is empty", line_number=line_number, field="client")

    balance = _number(row, "balance", line_number)
    if balance < 0:
        raise RecordValidationError("Balance must be >= 0", line_number=line_number,
                                    field="balance")

    operation = (row.get("operation") or "").strip().lower()
    if operation not in config.allowed_operations:
        raise RecordValidationError(f"Operation {operation!r} is not allowed",
                                    line_number=line_number, field="operation")

    amount = _number(row, "amount", line_number)
    if not 0 < amount <= config.max_amount:
        raise RecordValidationError(f"Amount must be in (0, {config.max_amount:g}]",
                                    line_number=line_number, field="amount")

    if operation == "deposit":
        after = balance + amount
    else:
        after = balance - amount
        if after < 0:
            raise InsufficientFundsError("Withdrawal would make the balance negative",
                                         line_number=line_number, field="amount")
    return Operation(number, client, operation, round(amount, 2),
                     round(balance, 2), round(after, 2))
