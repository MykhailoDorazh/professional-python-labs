"""Tests of the business logic (run: python -m unittest discover tests)."""

import unittest

from bank_accounts.exceptions import (
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
)
from bank_accounts.models import Account
from bank_accounts.services import (
    calculate_total,
    deposit,
    find_account,
    open_account,
    search_accounts,
    sort_accounts,
    withdraw,
)


def make_accounts() -> list[Account]:
    return [
        Account("Іван Петренко", "UA100001", 100.0),
        Account("Олена Коваль", "UA100002", 500.0),
        Account("Андрій Мельник", "UA100003", 0.0),
    ]


class ServicesTest(unittest.TestCase):
    def test_deposit_and_withdraw(self) -> None:
        account = make_accounts()[0]
        self.assertEqual(deposit(account, 50.5), 150.5)
        self.assertEqual(withdraw(account, 150.5), 0.0)

    def test_negative_balance_is_forbidden(self) -> None:
        account = make_accounts()[0]
        with self.assertRaises(InsufficientFundsError):
            withdraw(account, 100.01)
        self.assertEqual(account.balance, 100.0)

    def test_invalid_amount(self) -> None:
        account = make_accounts()[0]
        with self.assertRaises(InvalidAmountError):
            deposit(account, -5)

    def test_find_account(self) -> None:
        accounts = make_accounts()
        self.assertEqual(find_account(accounts, "ua100002").client_name,
                         "Олена Коваль")
        with self.assertRaises(AccountNotFoundError):
            find_account(accounts, "UA999999")

    def test_total_and_sort(self) -> None:
        accounts = make_accounts()
        self.assertEqual(calculate_total(accounts), 600.0)
        self.assertEqual(sort_accounts(accounts)[0].account_number, "UA100002")

    def test_search_by_several_criteria(self) -> None:
        found = search_accounts(make_accounts(), "о", min_balance=200)
        self.assertEqual([a.account_number for a in found], ["UA100002"])

    def test_open_account_validation(self) -> None:
        accounts = make_accounts()
        with self.assertRaises(InvalidAccountError):
            open_account(accounts, "Тест", "UA100001")
        with self.assertRaises(InvalidAccountError):
            open_account(accounts, "Тест", "12345")
        with self.assertRaises(InvalidAccountError):
            Account("Тест", "UA100009", -1)


if __name__ == "__main__":
    unittest.main()
