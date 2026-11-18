"""Aggregation and statistics of bank accounts."""

import json
from pathlib import Path
from typing import Any

from bank_analytics.data import ACCOUNT_TYPES
from bank_analytics.decorators import log_operation, measure_time
from bank_analytics.processors import Account, group_by_type


@measure_time
def total_balance(accounts: list[Account]) -> float:
    """Total amount of money (generator expression, no intermediate list)."""
    return round(sum(account["balance"] for account in accounts), 2)


def average_balance(accounts: list[Account]) -> float:
    """Average balance."""
    if not accounts:
        return 0.0
    return round(sum(a["balance"] for a in accounts) / len(accounts), 2)


@log_operation("пошук найбільшого балансу")
def richest_account(accounts: list[Account]) -> Account | None:
    """Account with the largest balance (max + lambda). O(n)."""
    if not accounts:
        return None
    return max(accounts, key=lambda account: account["balance"])


def balance_range(accounts: list[Account]) -> tuple[float, float]:
    """(minimum, maximum) balance as an immutable tuple."""
    balances = [account["balance"] for account in accounts]
    return min(balances), max(balances)


def sum_values(*values: float) -> float:
    """Sum of any number of positional arguments (*args)."""
    return round(sum(values), 2)


def create_account(**fields: Any) -> Account:
    """Create an account record from keyword arguments (**kwargs)."""
    required = {"number", "client", "balance", "type"}
    missing = required - fields.keys()
    if missing:
        raise ValueError(f"Відсутні поля: {', '.join(sorted(missing))}")
    if fields["type"] not in ACCOUNT_TYPES:
        raise ValueError(f"Невідомий тип рахунку: {fields['type']}")
    if fields["balance"] < 0:
        raise ValueError("Баланс не може бути від'ємним")
    return dict(fields)


def type_summary(accounts: list[Account]) -> dict[str, tuple[int, float, float]]:
    """type -> (count, total, average), built by dict comprehension."""
    groups = group_by_type(accounts)
    return {
        type_: (
            len(items),
            round(sum(a["balance"] for a in items), 2),
            round(sum(a["balance"] for a in items) / len(items), 2),
        )
        for type_, items in groups.items()
    }


def export_summary(path: Path, **summary: Any) -> Path:
    """Export the summary to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path
