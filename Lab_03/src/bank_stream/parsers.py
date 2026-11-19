"""Cleaning, parsing and validation stages."""

import csv
import re
from collections import Counter
from collections.abc import Iterable, Iterator

from bank_stream.models import ACCOUNT_NUMBER_PATTERN, OPERATIONS, Operation

_NUMBER_RE = re.compile(ACCOUNT_NUMBER_PATTERN)


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Skip empty lines and comments (#...)."""
    for line in lines:
        value = line.strip()
        if value and not value.startswith("#"):
            yield value + "\n"


def parse_csv_rows(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    """CSV lines -> dicts. csv.DictReader is lazy itself."""
    yield from csv.DictReader(lines)


def validate_operations(
    rows: Iterable[dict[str, str]],
    stats: Counter[str] | None = None,
) -> Iterator[Operation]:
    """Validation: account number, client, balance >= 0, amount > 0, operation.

    Invalid records are skipped; reasons are counted in `stats`.
    """
    for row in rows:
        reason = None
        try:
            number = (row["account_number"] or "").strip().upper()
            client = (row["client"] or "").strip()
            balance = float(row["balance"])
            operation = (row["operation"] or "").strip().lower()
            amount = float(row["amount"])
        except (KeyError, TypeError, ValueError):
            reason = "invalid:format"
        else:
            if not _NUMBER_RE.fullmatch(number):
                reason = "invalid:account_number"
            elif not client:
                reason = "invalid:client"
            elif balance < 0:
                reason = "invalid:balance"
            elif amount <= 0:
                reason = "invalid:amount"
            elif operation not in OPERATIONS:
                reason = "invalid:operation"

        if reason:
            if stats is not None:
                stats[reason] += 1
            continue
        yield Operation(number, client, balance, operation, amount)
