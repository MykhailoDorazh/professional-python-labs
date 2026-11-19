"""Service layer over a real SQLite test DB: money operations, transfer, rollback."""

from decimal import Decimal

import pytest
from bank_perf.exceptions import (
    AccountNotEmptyError,
    AccountNotFoundError,
    BankError,
    ClientNotFoundError,
    DuplicateAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)
from bank_perf.repositories import TransactionRepository
from bank_perf.services import BankService


def balances(bank: BankService) -> dict[str, Decimal]:
    bank.session.expire_all()  # read the committed state from the database
    return {a.number: bank.get_balance(a.number) for a in bank.accounts.get_all()}


def test_open_account_with_initial_deposit(seeded: BankService) -> None:
    assert balances(seeded) == {"UA1": Decimal("1000.00"), "UA2": Decimal("500.00"),
                                "UA3": Decimal("0.00")}
    assert [t.kind for t in seeded.history("UA1")] == ["deposit"]
    assert seeded.get_account("UA2").account_type == "savings"


def test_deposit_and_withdraw(seeded: BankService) -> None:
    seeded.deposit("UA3", "150.25")
    tx = seeded.withdraw("UA3", Decimal("50.25"))
    assert seeded.get_balance("UA3") == Decimal("100.00")
    assert (tx.kind, tx.amount_cents, tx.balance_after_cents) == ("withdraw", 5025, 10000)


def test_withdraw_whole_balance_is_allowed(seeded: BankService) -> None:
    seeded.withdraw("UA2", "500")
    assert seeded.get_balance("UA2") == Decimal("0.00")


def test_negative_balance_is_forbidden(seeded: BankService) -> None:
    with pytest.raises(InsufficientFundsError):
        seeded.withdraw("UA2", "500.01")
    assert balances(seeded)["UA2"] == Decimal("500.00")
    assert len(seeded.history("UA2")) == 1  # no history record for a failed operation


@pytest.mark.parametrize("amount", ["0", "-10", "abc", "1.001", "NaN"])
def test_invalid_amount(seeded: BankService, amount: str) -> None:
    with pytest.raises(InvalidAmountError):
        seeded.deposit("UA1", amount)


def test_unknown_account_and_client(seeded: BankService) -> None:
    with pytest.raises(AccountNotFoundError):
        seeded.deposit("UA404", "10")
    with pytest.raises(ClientNotFoundError):
        seeded.get_client(404)
    with pytest.raises(ClientNotFoundError):
        seeded.open_account(404, "UA9")


def test_duplicate_account_number(seeded: BankService) -> None:
    with pytest.raises(DuplicateAccountError):
        seeded.open_account(1, "UA1")
    assert seeded.accounts.count() == 3  # session is still usable after the rollback


def test_total_funds_and_turnover(seeded: BankService) -> None:
    assert seeded.total_funds() == Decimal("1500.00")
    seeded.transfer_money("UA1", "UA3", "200")
    seeded.withdraw("UA2", "100")
    assert seeded.total_funds() == Decimal("1400.00")
    assert seeded.turnover() == Decimal("1800.00")  # 1000 + 500 + 200 + 100


def test_successful_transfer(seeded: BankService) -> None:
    out, inc = seeded.transfer_money("UA1", "UA3", "250.50")
    assert balances(seeded) == {"UA1": Decimal("749.50"), "UA2": Decimal("500.00"),
                                "UA3": Decimal("250.50")}
    assert (out.kind, out.counterparty) == ("transfer_out", "UA3")
    assert (inc.kind, inc.counterparty) == ("transfer_in", "UA1")
    assert [t.kind for t in seeded.history("UA3")] == ["transfer_in"]


def test_transfer_rollback_on_unknown_target(seeded: BankService) -> None:
    with pytest.raises(AccountNotFoundError):
        seeded.transfer_money("UA1", "UA404", "300")
    assert balances(seeded)["UA1"] == Decimal("1000.00")   # debit was rolled back
    assert len(seeded.history("UA1")) == 1                  # transfer_out was rolled back


def test_transfer_rollback_on_insufficient_funds(seeded: BankService) -> None:
    with pytest.raises(InsufficientFundsError):
        seeded.transfer_money("UA2", "UA1", "500.01")
    assert balances(seeded) == {"UA1": Decimal("1000.00"), "UA2": Decimal("500.00"),
                                "UA3": Decimal("0.00")}


def test_transfer_rollback_on_failure_in_the_middle(
    seeded: BankService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure injection: the 2nd history INSERT fails after the debit was flushed."""
    original_add = TransactionRepository.add
    calls = {"n": 0}

    def flaky_add(self: TransactionRepository, entity):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("database connection lost")
        return original_add(self, entity)

    monkeypatch.setattr(TransactionRepository, "add", flaky_add)
    with pytest.raises(RuntimeError):
        seeded.transfer_money("UA1", "UA3", "400")
    monkeypatch.undo()
    assert balances(seeded) == {"UA1": Decimal("1000.00"), "UA2": Decimal("500.00"),
                                "UA3": Decimal("0.00")}
    assert seeded.transactions.count() == 2  # only the two initial deposits


def test_transfer_to_same_account(seeded: BankService) -> None:
    with pytest.raises(BankError):
        seeded.transfer_money("UA1", "UA1", "1")


def test_close_account(seeded: BankService) -> None:
    seeded.close_account("UA3")
    with pytest.raises(AccountNotFoundError):
        seeded.get_account("UA3")
    with pytest.raises(AccountNotEmptyError):
        seeded.close_account("UA1")


def test_rename_and_delete_client(seeded: BankService) -> None:
    seeded.rename_client(2, "Олег Мельник-Шевченко")
    assert seeded.get_client(2).full_name == "Олег Мельник-Шевченко"
    seeded.delete_client(1)
    assert seeded.accounts.count() == 1        # UA1, UA2 removed by ON DELETE CASCADE
    assert seeded.transactions.count() == 0


def test_change_account_type(seeded: BankService) -> None:
    assert seeded.change_account_type("UA1", "savings").account_type == "savings"
    with pytest.raises(BankError):
        seeded.change_account_type("UA1", "crypto")


def test_reports_group_by(seeded: BankService) -> None:
    seeded.transfer_money("UA1", "UA3", "100")
    summary = seeded.client_summary()
    assert summary[0] == ("Анна Коваль", 2, Decimal("1400.00"))
    assert summary[1] == ("Олег Мельник", 1, Decimal("100.00"))
    stats = {kind: (count, total) for kind, count, total, _ in seeded.transactions.stats_by_kind()}
    assert stats == {"deposit": (2, 150000), "transfer_in": (1, 10000),
                     "transfer_out": (1, 10000)}

