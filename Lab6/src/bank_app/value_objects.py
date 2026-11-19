"""Immutable value objects: Money and AccountNumber."""

import re
from dataclasses import dataclass
from functools import total_ordering

from bank_app.exceptions import CurrencyMismatchError, InvalidAccountError

DEFAULT_CURRENCY = "UAH"
ACCOUNT_NUMBER_RE = re.compile(r"UA\d{6}")


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Non-negative amount of money in one currency."""

    amount: float
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        # frozen=True забороняє звичайне присвоєння, тому округлення - через object.__setattr__
        object.__setattr__(self, "amount", round(float(self.amount), 2))

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        return cls(0.0, currency)

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(f"{self.currency} != {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: float) -> "Money":
        return Money(self.amount * factor, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __bool__(self) -> bool:
        return self.amount > 0

    def __str__(self) -> str:
        return f"{self.amount:,.2f} {self.currency}".replace(",", " ")


@dataclass(frozen=True, slots=True)
class AccountNumber:
    """Account number in format UA + 6 digits."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not ACCOUNT_NUMBER_RE.fullmatch(normalized):
            raise InvalidAccountError(f"Некоректний номер рахунку: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    @property
    def masked(self) -> str:
        """Number for logs and notifications: UA****01."""
        return f"{self.value[:2]}****{self.value[-2:]}"

    def __str__(self) -> str:
        return self.value
