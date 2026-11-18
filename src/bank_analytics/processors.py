"""Processing of account records: search, index, grouping, filtering, sorting."""

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from bank_analytics.decorators import log_operation

Account = dict[str, Any]
Predicate = Callable[[Account], bool]


# ---------- пошук ----------

def find_account_linear(accounts: list[Account], number: str) -> Account | None:
    """Linear search in a list. Complexity: O(n)."""
    for account in accounts:
        if account["number"] == number:
            return account
    return None


def create_account_index(accounts: list[Account]) -> dict[str, Account]:
    """dict-index by account number (dict comprehension). Build: O(n)."""
    return {account["number"]: account for account in accounts}


@log_operation("пошук за номером")
def find_by_number(index: dict[str, Account], number: str) -> Account | None:
    """Search in the dict-index. Complexity: O(1) on average."""
    return index.get(number)


# ---------- множини ----------

def get_unique_clients(accounts: list[Account]) -> set[str]:
    """Unique clients (set comprehension). O(n)."""
    return {account["client"] for account in accounts}


def get_used_types(accounts: list[Account]) -> set[str]:
    """Account types that actually occur in the data."""
    return {account["type"] for account in accounts}


# ---------- групування ----------

@log_operation("групування за типом")
def group_by_type(accounts: list[Account]) -> dict[str, list[Account]]:
    """Group accounts by type using defaultdict(list). O(n)."""
    groups: defaultdict[str, list[Account]] = defaultdict(list)
    for account in accounts:
        groups[account["type"]].append(account)
    return dict(groups)


def group_nested(accounts: list[Account]) -> dict[str, dict[str, list[str]]]:
    """Nested grouping: type -> client -> list of account numbers."""
    result: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for account in accounts:
        result[account["type"]][account["client"]].append(account["number"])
    return {type_: dict(clients) for type_, clients in result.items()}


def count_by_type(accounts: list[Account]) -> Counter[str]:
    """Number of accounts of every type (Counter + generator expression)."""
    return Counter(account["type"] for account in accounts)


# ---------- фільтрація ----------

def filter_items(items: list[Account], predicate: Predicate) -> list[Account]:
    """Universal filter: keeps items for which predicate(item) is True."""
    return [item for item in items if predicate(item)]


def make_min_balance_filter(minimum: float) -> Predicate:
    """Closure: the inner function remembers `minimum`."""

    def predicate(account: Account) -> bool:
        return account["balance"] >= minimum

    return predicate


def make_type_filter(*types: str) -> Predicate:
    """Closure over *args: account type must be one of the given types."""
    allowed = set(types)

    def predicate(account: Account) -> bool:
        return account["type"] in allowed

    return predicate


@log_operation("фільтрація за мінімальним балансом")
def filter_by_min_balance(accounts: list[Account], minimum: float) -> list[Account]:
    """Accounts with balance >= minimum."""
    return filter_items(accounts, make_min_balance_filter(minimum))


# ---------- сортування ----------

def sort_items(items: list[Account], *keys: str, reverse: bool = False) -> list[Account]:
    """Universal sorting by one or several fields. O(n log n)."""
    return sorted(items, key=lambda item: tuple(item[k] for k in keys), reverse=reverse)


@log_operation("сортування за балансом")
def sort_by_balance(accounts: list[Account], descending: bool = True) -> list[Account]:
    """Sort accounts by balance (lambda as the key)."""
    return sorted(accounts, key=lambda account: account["balance"], reverse=descending)


# ---------- конвеєр ----------

def pipeline(data: list[Account], *steps: Callable[[list[Account]], list[Account]]) -> list[Account]:
    """Apply processing steps one after another."""
    for step in steps:
        data = step(data)
    return data
