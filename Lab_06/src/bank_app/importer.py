"""CSV import of accounts and operations (streaming, strict/tolerant)."""

import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from bank_app.config import AppConfig
from bank_app.exceptions import BankError, DataImportError, RecordValidationError
from bank_app.models import Account, CurrentAccount, Customer, SavingsAccount
from bank_app.value_objects import Money

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OperationRecord:
    line_number: int
    account_number: str
    operation: str
    amount: Money


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    errors: list[str] = field(default_factory=list)


def read_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            for line_number, row in enumerate(csv.DictReader(file), start=2):
                yield line_number, row
    except OSError as error:
        raise DataImportError(f"Cannot read {path}") from error


def parse_amount(text: str | None, *, line_number: int, field_name: str) -> float:
    try:
        return float(text or "")
    except ValueError as error:
        raise RecordValidationError(f"{field_name} must be numeric",
                                    line_number=line_number, field=field_name) from error


def parse_account(row: dict[str, str], line_number: int, currency: str) -> Account:
    try:
        owner = Customer(int(row["owner_id"]), row["owner_name"], row["owner_email"])
        balance = Money(parse_amount(row["balance"], line_number=line_number,
                                     field_name="balance"), currency)
        if row["type"] == "savings":
            return SavingsAccount(row["number"], owner, balance)
        if row["type"] == "current":
            return CurrentAccount(row["number"], owner, balance)
    except RecordValidationError:
        raise
    except (KeyError, ValueError, BankError) as error:
        raise RecordValidationError(f"Invalid account record: {error}",
                                    line_number=line_number) from error
    raise RecordValidationError(f"Unknown account type {row['type']!r}",
                                line_number=line_number, field="type")


def import_accounts(path: Path, currency: str = "UAH") -> list[Account]:
    """Accounts file is small and must be fully valid (strict)."""
    return [parse_account(row, line, currency) for line, row in read_rows(path)]


def parse_operation(row: dict[str, str], line_number: int, config: AppConfig) -> OperationRecord:
    operation = (row.get("operation") or "").strip().lower()
    if operation not in config.allowed_operations:
        raise RecordValidationError(f"Operation {operation!r} is not allowed",
                                    line_number=line_number, field="operation")
    amount = parse_amount(row.get("amount"), line_number=line_number, field_name="amount")
    if not 0 < amount <= config.max_amount:
        raise RecordValidationError("Amount out of range", line_number=line_number,
                                    field="amount")
    number = (row.get("account_number") or "").strip().upper()
    return OperationRecord(line_number, number, operation, Money(amount, config.currency))


def read_operations(path: Path, config: AppConfig,
                    statistics: ImportStatistics) -> Iterator[OperationRecord]:
    for line_number, row in read_rows(path):
        statistics.total += 1
        try:
            record = parse_operation(row, line_number, config)
        except RecordValidationError as error:
            statistics.invalid += 1
            statistics.errors.append(f"line {line_number}: {error}")
            logger.warning("Invalid operation at line %s: %s", line_number, error)
            if config.skip_invalid:
                continue
            raise
        statistics.valid += 1
        yield record
