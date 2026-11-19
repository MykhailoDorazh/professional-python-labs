"""Data models of the bank accounts system."""

import re
from dataclasses import dataclass

from bank_accounts.config import (
    ACCOUNT_NUMBER_PATTERN,
    CURRENCY,
    MIN_BALANCE,
)
from bank_accounts.exceptions import InvalidAccountError


@dataclass
class Account:
    """Bank account: client name, account number and balance."""

    client_name: str
    account_number: str
    balance: float = 0.0

    def __post_init__(self) -> None:
        self.client_name = self.client_name.strip()
        self.account_number = self.account_number.strip().upper()

        if not self.client_name:
            raise InvalidAccountError("Ім'я клієнта не може бути порожнім")
        if not re.fullmatch(ACCOUNT_NUMBER_PATTERN, self.account_number):
            raise InvalidAccountError(
                f"Некоректний номер рахунку: {self.account_number!r} "
                "(очікується формат UA123456)"
            )
        if self.balance < MIN_BALANCE:
            raise InvalidAccountError("Баланс не може бути від'ємним")

    @property
    def formatted_balance(self) -> str:
        return f"{self.balance:,.2f} {CURRENCY}".replace(",", " ")
