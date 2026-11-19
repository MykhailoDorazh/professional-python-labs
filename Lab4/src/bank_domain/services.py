"""Application/service layer and concrete adapters."""

from collections import defaultdict
from collections.abc import Iterable
from typing import TypeVar

from bank_domain.dto import SummaryPayload
from bank_domain.exceptions import AccountNotFoundError, DuplicateAccountError
from bank_domain.models import Account, Transaction
from bank_domain.protocols import AccountReader, AccountStore, Notifier
from bank_domain.value_objects import DEFAULT_CURRENCY, Money

Number = TypeVar("Number", int, float)  # constrained TypeVar


def clamp(value: Number, low: Number, high: Number) -> Number:
    """Keep value in [low, high]; result has the same type as the input."""
    return max(low, min(value, high))


# ---------- concrete adapters (не успадковують Notifier: structural typing) ----------

class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"    [notify -> {recipient}] {message}")


class InMemoryNotifier:
    """Stores messages instead of sending them (useful for tests)."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))


# ---------- application services ----------

class BankService:
    """Use cases: open account, deposit, withdraw, balance, search.
    Dependencies are injected through the constructor (DIP)."""

    def __init__(self, accounts: AccountStore, notifier: Notifier) -> None:
        self._accounts = accounts
        self._notifier = notifier

    def open_account(self, account: Account) -> Account:
        if self._accounts.get(account.number) is not None:
            raise DuplicateAccountError(f"Рахунок {account.number} вже існує")
        self._accounts.add(account)
        self._notifier.send(account.owner.email,
                            f"Відкрито рахунок {account.masked_number}")
        return account

    def find_account(self, number: str) -> Account:
        account = self._accounts.get(number)
        if account is None:
            raise AccountNotFoundError(f"Рахунок {number} не знайдено")
        return account

    def find_by_owner(self, name_part: str) -> list[Account]:
        text = name_part.lower()
        return [a for a in self._accounts if text in a.owner.name.lower()]

    def deposit(self, number: str, amount: Money) -> Transaction:
        account = self.find_account(number)
        transaction = account.deposit(amount)
        self._notify(account, f"Зараховано {amount}")
        return transaction

    def withdraw(self, number: str, amount: Money) -> Transaction:
        account = self.find_account(number)
        transaction = account.withdraw(amount)  # InsufficientFundsError, якщо грошей мало
        self._notify(account, f"Списано {amount}")
        return transaction

    def get_balance(self, number: str) -> Money:
        return self.find_account(number).balance

    def close_month(self) -> list[Transaction]:
        return [t for account in self._accounts if (t := account.close_month()) is not None]

    def _notify(self, account: Account, text: str) -> None:
        # у повідомленнях лише маскований номер - без повних реквізитів
        self._notifier.send(account.owner.email,
                            f"{account.masked_number}: {text}, баланс {account.balance}")


class ReportService:
    """Reporting depends only on the read interface (ISP)."""

    def __init__(self, accounts: AccountReader) -> None:
        self._accounts = accounts

    def total_funds(self, currency: str = DEFAULT_CURRENCY) -> Money:
        total = Money.zero(currency)
        for account in self._accounts:
            if account.balance.currency == currency:
                total = total + account.balance
        return total

    def totals_by_type(self) -> dict[str, Money]:
        totals: defaultdict[str, Money] = defaultdict(Money.zero)
        for account in self._accounts:
            totals[account.account_type] = totals[account.account_type] + account.balance
        return dict(totals)

    def richest(self) -> Account | None:
        return max(self._accounts, default=None)  # Account.__lt__ порівнює баланси

    def ranking(self) -> list[Account]:
        return sorted(self._accounts, reverse=True)

    def summary(self) -> SummaryPayload:
        items = list(self._accounts)
        return {
            "accounts": len(items),
            "total": self.total_funds().amount,
            "currency": DEFAULT_CURRENCY,
            "by_type": {k: v.amount for k, v in self.totals_by_type().items()},
        }


def total_of(accounts: Iterable[Account]) -> Money:
    return sum((a.balance for a in accounts), start=Money.zero())
