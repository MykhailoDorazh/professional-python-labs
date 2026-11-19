"""Application services and simple adapters."""

import logging
from collections import defaultdict

from bank_app.exceptions import AccountNotFoundError, DuplicateAccountError
from bank_app.models import Account, Transaction
from bank_app.protocols import AccountReader, AccountStore, Notifier
from bank_app.value_objects import DEFAULT_CURRENCY, Money

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"    [notify -> {recipient}] {message}")


class BankService:
    """Use cases of the bank. Dependencies are injected (repository, notifier)."""

    def __init__(self, accounts: AccountStore, notifier: Notifier) -> None:
        self._accounts = accounts
        self._notifier = notifier
        self.failed_notifications = 0

    def open_account(self, account: Account) -> Account:
        if self._accounts.get(account.number) is not None:
            raise DuplicateAccountError(f"Рахунок {account.number} вже існує")
        self._accounts.add(account)
        self._notify(account, "рахунок відкрито")
        return account

    def find_account(self, number: str) -> Account:
        account = self._accounts.get(number)
        if account is None:
            raise AccountNotFoundError(f"Рахунок {number} не знайдено")
        return account

    def get_balance(self, number: str) -> Money:
        return self.find_account(number).balance

    def deposit(self, number: str, amount: Money) -> Transaction:
        account = self.find_account(number)
        transaction = account.deposit(amount)
        self._notify(account, f"зараховано {amount}")
        return transaction

    def withdraw(self, number: str, amount: Money) -> Transaction:
        account = self.find_account(number)
        transaction = account.withdraw(amount)
        self._notify(account, f"списано {amount}")
        return transaction

    def _notify(self, account: Account, text: str) -> None:
        """A failed notification must not cancel a completed bank operation."""
        try:
            self._notifier.send(account.owner.email, f"{account.masked_number}: {text}")
        except Exception as error:  # зовнішня система: будь-яка її помилка
            self.failed_notifications += 1
            logger.warning("Notification for %s failed: %s", account.masked_number, error)


class ReportService:
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
        return max(self._accounts, default=None)

    def average_balance(self) -> float:
        balances = [account.balance.amount for account in self._accounts]
        return sum(balances) / len(balances) if balances else 0.0
