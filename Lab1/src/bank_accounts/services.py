"""Business logic of the bank accounts system."""

from bank_accounts.config import MAX_OPERATION_AMOUNT, MIN_BALANCE
from bank_accounts.exceptions import (
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
)
from bank_accounts.models import Account


def validate_amount(amount: float) -> None:
    """Check that the amount of an operation is positive and not too big."""
    if amount <= 0:
        raise InvalidAmountError("Сума операції має бути додатною")
    if amount > MAX_OPERATION_AMOUNT:
        raise InvalidAmountError(
            f"Сума операції перевищує ліміт {MAX_OPERATION_AMOUNT:.2f}"
        )


def deposit(account: Account, amount: float) -> float:
    """Top up the account. Returns the new balance."""
    validate_amount(amount)
    account.balance = round(account.balance + amount, 2)
    return account.balance


def withdraw(account: Account, amount: float) -> float:
    """Withdraw money. A negative balance is not allowed."""
    validate_amount(amount)
    if account.balance - amount < MIN_BALANCE:
        raise InsufficientFundsError(
            f"Недостатньо коштів на {account.account_number}: "
            f"баланс {account.balance:.2f}, запит {amount:.2f}"
        )
    account.balance = round(account.balance - amount, 2)
    return account.balance


def get_balance(account: Account) -> float:
    """Return the current balance of the account."""
    return account.balance


def find_account(accounts: list[Account], account_number: str) -> Account:
    """Find an account by its number (case-insensitive)."""
    number = account_number.strip().upper()
    for account in accounts:
        if account.account_number == number:
            return account
    raise AccountNotFoundError(f"Рахунок {number} не знайдено")


def find_by_client(accounts: list[Account], name_part: str) -> list[Account]:
    """Find all accounts whose client name contains the given text."""
    text = name_part.strip().lower()
    return [
        account
        for account in accounts
        if text in account.client_name.lower()
    ]


def search_accounts(
    accounts: list[Account],
    name_part: str = "",
    min_balance: float | None = None,
    max_balance: float | None = None,
) -> list[Account]:
    """Search by several criteria at once: client name and balance range."""
    result = find_by_client(accounts, name_part)
    if min_balance is not None:
        result = [a for a in result if a.balance >= min_balance]
    if max_balance is not None:
        result = [a for a in result if a.balance <= max_balance]
    return result


def open_account(
    accounts: list[Account],
    client_name: str,
    account_number: str,
    initial_balance: float = 0.0,
) -> Account:
    """Create a new account and add it to the list. Numbers must be unique."""
    account = Account(client_name, account_number, initial_balance)
    if any(a.account_number == account.account_number for a in accounts):
        raise InvalidAccountError(
            f"Рахунок {account.account_number} вже існує"
        )
    accounts.append(account)
    return account


def calculate_total(accounts: list[Account]) -> float:
    """Total amount of money on all accounts."""
    return round(sum(account.balance for account in accounts), 2)


def sort_accounts(
    accounts: list[Account],
    by: str = "balance",
    descending: bool = True,
) -> list[Account]:
    """Return accounts sorted by balance, client name or account number."""
    keys = {
        "balance": lambda a: a.balance,
        "client": lambda a: a.client_name.lower(),
        "number": lambda a: a.account_number,
    }
    if by not in keys:
        raise ValueError(f"Невідоме поле сортування: {by}")
    return sorted(accounts, key=keys[by], reverse=descending)


def calculate_statistics(accounts: list[Account]) -> dict[str, float]:
    """Count, total, average, minimum and maximum balance."""
    if not accounts:
        return {"count": 0, "total": 0.0, "average": 0.0,
                "minimum": 0.0, "maximum": 0.0}
    balances = [account.balance for account in accounts]
    total = sum(balances)
    return {
        "count": len(balances),
        "total": round(total, 2),
        "average": round(total / len(balances), 2),
        "minimum": min(balances),
        "maximum": max(balances),
    }
