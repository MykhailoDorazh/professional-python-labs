"""Domain entities: Customer, Transaction, Account and its subclasses."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import ClassVar

from bank_app.exceptions import (
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
)
from bank_app.value_objects import AccountNumber, Money


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    INTEREST = "interest"
    FEE = "fee"


@dataclass(frozen=True, slots=True)
class Transaction:
    """Immutable record of one operation on an account."""

    id: int
    account_number: str
    kind: TransactionType
    amount: Money
    balance_after: Money

    def __str__(self) -> str:
        return (f"#{self.id} {self.account_number} {self.kind.value:<8} "
                f"{self.amount} -> баланс {self.balance_after}")


@dataclass(slots=True)
class Customer:
    """Bank client."""

    id: int
    name: str
    email: str

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise InvalidAccountError("Ім'я клієнта не може бути порожнім")
        if "@" not in self.email:
            raise InvalidAccountError(f"Некоректний email: {self.email!r}")


class Account(ABC):
    """Abstract bank account. Balance is encapsulated: it changes only
    through deposit()/withdraw(), so a negative balance is impossible."""

    account_type: ClassVar[str] = "account"
    _transaction_ids: ClassVar[Iterator[int]] = count(1)  # спільний для всіх рахунків

    def __init__(self, number: str, owner: Customer, opening_balance: Money | None = None) -> None:
        self._number = AccountNumber(number)
        self._owner = owner  # composition: рахунок "має" клієнта
        self._balance = opening_balance or Money.zero()
        self._transactions: list[Transaction] = []  # composition: історія операцій

    # ---------- properties (read-only interface) ----------
    @property
    def number(self) -> str:
        return self._number.value

    @property
    def key(self) -> str:
        """Key for the generic repository."""
        return self._number.value

    @property
    def masked_number(self) -> str:
        return self._number.masked

    @property
    def owner(self) -> Customer:
        return self._owner

    @property
    def balance(self) -> Money:
        return self._balance

    # ---------- behavior ----------
    def deposit(self, amount: Money) -> Transaction:
        self._validate_amount(amount)
        self._balance = self._balance + amount
        return self._record(TransactionType.DEPOSIT, amount)

    def withdraw(self, amount: Money) -> Transaction:
        self._validate_amount(amount)
        available = self.available_for_withdrawal()
        if amount > available:
            raise InsufficientFundsError(self.number, str(amount), str(available))
        self._balance = self._balance - amount
        return self._record(TransactionType.WITHDRAW, amount)

    @abstractmethod
    def available_for_withdrawal(self) -> Money:
        """How much money may be withdrawn now."""

    @abstractmethod
    def close_month(self) -> Transaction | None:
        """End-of-month processing (interest or fee)."""

    # ---------- helpers ----------
    def _validate_amount(self, amount: Money) -> None:
        if amount.amount <= 0:
            raise InvalidAmountError("Сума операції має бути додатною")

    def _record(self, kind: TransactionType, amount: Money) -> Transaction:
        transaction = Transaction(next(Account._transaction_ids), self.number,
                                  kind, amount, self._balance)
        self._transactions.append(transaction)
        return transaction

    # ---------- dunder methods ----------
    def __repr__(self) -> str:
        return (f"{type(self).__name__}(number={self.number!r}, "
                f"owner={self._owner.name!r}, balance={self._balance.amount!r})")

    def __str__(self) -> str:
        return f"{self.number} [{self.account_type}] {self._owner.name}: {self._balance}"

    def __len__(self) -> int:
        return len(self._transactions)

    def __iter__(self) -> Iterator[Transaction]:
        return iter(self._transactions)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Account) and self.number == other.number

    def __hash__(self) -> int:
        return hash(self.number)

    def __lt__(self, other: "Account") -> bool:
        return self._balance < other._balance


class SavingsAccount(Account):
    """Savings account: keeps a minimum balance, earns monthly interest."""

    account_type = "savings"

    def __init__(self, number: str, owner: Customer, opening_balance: Money | None = None,
                 *, interest_rate: float = 0.01, minimum_balance: Money | None = None) -> None:
        super().__init__(number, owner, opening_balance)
        if not 0 <= interest_rate <= 0.1:
            raise InvalidAmountError("Ставка має бути в межах 0..10 %")
        self.interest_rate = interest_rate
        self.minimum_balance = minimum_balance or Money.zero(self.balance.currency)

    def available_for_withdrawal(self) -> Money:
        if self.balance > self.minimum_balance:
            return self.balance - self.minimum_balance
        return Money.zero(self.balance.currency)

    def close_month(self) -> Transaction | None:
        interest = self.balance * self.interest_rate
        if not interest:
            return None
        self._balance = self._balance + interest
        return self._record(TransactionType.INTEREST, interest)


class CurrentAccount(Account):
    """Current account: whole balance is available, monthly service fee."""

    account_type = "current"

    def __init__(self, number: str, owner: Customer, opening_balance: Money | None = None,
                 *, monthly_fee: Money | None = None) -> None:
        super().__init__(number, owner, opening_balance)
        self.monthly_fee = monthly_fee or Money(25.0, self.balance.currency)

    def available_for_withdrawal(self) -> Money:
        return self.balance

    def close_month(self) -> Transaction | None:
        fee = min(self.monthly_fee, self.balance)  # комісія не робить баланс від'ємним
        if not fee:
            return None
        self._balance = self._balance - fee
        return self._record(TransactionType.FEE, fee)
