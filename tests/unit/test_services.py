from collections.abc import Callable
from unittest.mock import Mock

import pytest

from bank_app.exceptions import (
    AccountNotFoundError,
    DuplicateAccountError,
    InsufficientFundsError,
)
from bank_app.models import Account
from bank_app.protocols import AccountStore
from bank_app.repositories import InMemoryRepository
from bank_app.services import BankService, ConsoleNotifier, ReportService
from bank_app.value_objects import Money


def test_open_account_sends_masked_notification(repository: InMemoryRepository[Account],
                                                notifier: Mock,
                                                current_account: Account) -> None:
    BankService(repository, notifier).open_account(current_account)
    assert "UA100001" in repository
    notifier.send.assert_called_once_with("ivan@example.com", "UA****01: рахунок відкрито")


def test_duplicate_account_rejected(bank: BankService,
                                    account_factory: Callable[..., Account]) -> None:
    with pytest.raises(DuplicateAccountError):
        bank.open_account(account_factory("UA100001"))


def test_find_and_balance(bank: BankService) -> None:
    assert bank.find_account("ua100001").number == "UA100001"
    assert bank.get_balance("UA100001") == Money(1000)
    with pytest.raises(AccountNotFoundError, match="UA999999"):
        bank.find_account("UA999999")


def test_deposit_and_withdraw_notify(bank: BankService, notifier: Mock) -> None:
    bank.deposit("UA100001", Money(500))
    bank.withdraw("UA100001", Money(300))
    assert bank.get_balance("UA100001") == Money(1200)
    assert notifier.send.call_count == 2
    notifier.send.assert_called_with("ivan@example.com", "UA****01: списано 300.00 UAH")


def test_insufficient_funds_does_not_notify(bank: BankService, notifier: Mock) -> None:
    with pytest.raises(InsufficientFundsError):
        bank.withdraw("UA100001", Money(1000.01))
    notifier.send.assert_not_called()
    assert bank.get_balance("UA100001") == Money(1000)


def test_notifier_failure_does_not_cancel_operation(bank: BankService, notifier: Mock) -> None:
    notifier.send.side_effect = ConnectionError("SMTP unavailable")
    bank.deposit("UA100001", Money(1))
    assert bank.get_balance("UA100001") == Money(1001)  # операцію виконано
    assert bank.failed_notifications == 1


def test_service_with_repository_mock(current_account: Account, notifier: Mock) -> None:
    repository = Mock(spec=AccountStore)
    repository.get.return_value = current_account
    bank = BankService(repository, notifier)
    assert bank.get_balance("UA100001") == Money(1000)
    repository.get.assert_called_once_with("UA100001")
    repository.get.return_value = None
    with pytest.raises(AccountNotFoundError):
        bank.get_balance("UA100002")


def test_reports(repository: InMemoryRepository[Account],
                 account_factory: Callable[..., Account]) -> None:
    for number, balance, kind in [("UA100001", 100.10, "current"),
                                  ("UA100002", 200.20, "current"),
                                  ("UA100003", 0.3, "savings")]:
        repository.add(account_factory(number, balance, kind))
    reports = ReportService(repository)
    assert reports.total_funds().amount == pytest.approx(300.6)
    assert reports.total_funds("USD") == Money(0, "USD")
    assert reports.totals_by_type()["savings"] == Money(0.3)
    assert reports.richest().number == "UA100002"  # type: ignore[union-attr]
    assert reports.average_balance() == pytest.approx(100.2)


def test_reports_on_empty_repository(repository: InMemoryRepository[Account]) -> None:
    reports = ReportService(repository)
    assert reports.total_funds() == Money(0)
    assert reports.richest() is None
    assert reports.average_balance() == 0.0


def test_console_notifier_prints(capsys: pytest.CaptureFixture[str]) -> None:
    ConsoleNotifier().send("a@b.c", "hello")
    assert "[notify -> a@b.c] hello" in capsys.readouterr().out


def test_repository_collection_protocol(repository: InMemoryRepository[Account],
                                        current_account: Account) -> None:
    repository.add(current_account)
    assert repository["ua100001"] is current_account
    assert repository.find(lambda a: a.balance.amount > 500) == [current_account]
    assert repository.all() == [current_account] and 5 not in repository
    assert repository.remove("UA100001") and not repository.remove("UA100001")


def test_repository_rejects_duplicate_key(repository: InMemoryRepository[Account],
                                          account_factory: Callable[..., Account]) -> None:
    repository.add(account_factory("UA100001"))
    with pytest.raises(DuplicateAccountError, match="UA100001"):
        repository.add(account_factory("UA100001", 5))
    assert len(repository) == 1
