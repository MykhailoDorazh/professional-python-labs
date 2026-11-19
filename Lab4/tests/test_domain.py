"""Tests of the domain model (run: python -m unittest discover tests)."""

import unittest

from bank_domain.exceptions import (
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
)
from bank_domain.models import CurrentAccount, Customer, SavingsAccount
from bank_domain.repositories import InMemoryRepository
from bank_domain.services import BankService, InMemoryNotifier, ReportService
from bank_domain.value_objects import Money


class DomainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Customer(1, "Іван Петренко", "ivan@example.com")
        self.repository: InMemoryRepository = InMemoryRepository()
        self.notifier = InMemoryNotifier()
        self.service = BankService(self.repository, self.notifier)
        self.service.open_account(CurrentAccount("UA100001", self.owner, Money(100)))
        self.service.open_account(SavingsAccount("UA100002", self.owner, Money(1000),
                                                 minimum_balance=Money(200)))

    def test_money_is_immutable_value_object(self) -> None:
        self.assertEqual(Money(1) + Money(2.5), Money(3.5))
        with self.assertRaises(ValueError):
            Money(-1)
        with self.assertRaises(CurrencyMismatchError):
            Money(1) + Money(1, "USD")

    def test_deposit_withdraw_and_negative_balance(self) -> None:
        self.service.deposit("UA100001", Money(50))
        self.service.withdraw("UA100001", Money(150))
        self.assertEqual(self.service.get_balance("UA100001"), Money(0))
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw("UA100001", Money(0.01))

    def test_savings_minimum_balance(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw("UA100002", Money(801))
        self.service.withdraw("UA100002", Money(800))

    def test_validation(self) -> None:
        with self.assertRaises(InvalidAmountError):
            self.service.deposit("UA100001", Money(0))
        with self.assertRaises(InvalidAccountError):
            CurrentAccount("12345", self.owner)
        with self.assertRaises(AccountNotFoundError):
            self.service.find_account("UA999999")

    def test_reports_and_notifications(self) -> None:
        reports = ReportService(self.repository)
        self.assertEqual(reports.total_funds(), Money(1100))
        self.assertEqual(reports.richest().number, "UA100002")
        self.assertEqual(len(self.notifier.messages), 2)
        self.assertNotIn("UA100001", self.notifier.messages[0][1])  # номер замаскований


if __name__ == "__main__":
    unittest.main()
