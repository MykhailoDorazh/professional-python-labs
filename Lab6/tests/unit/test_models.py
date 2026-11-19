from collections.abc import Callable

import pytest

from bank_app.exceptions import InsufficientFundsError, InvalidAccountError, InvalidAmountError
from bank_app.models import Account, Customer, SavingsAccount, TransactionType
from bank_app.value_objects import Money


def test_account_creation(current_account: Account) -> None:
    assert current_account.number == "UA100001"
    assert current_account.balance == Money(1000)
    assert current_account.account_type == "current"
    assert len(current_account) == 0


def test_invalid_account_number_rejected(owner: Customer) -> None:
    from bank_app.models import CurrentAccount

    with pytest.raises(InvalidAccountError):
        CurrentAccount("12345", owner)


@pytest.mark.parametrize("name, email", [("", "a@b.c"), ("Іван", "no-email")])
def test_invalid_customer(name: str, email: str) -> None:
    with pytest.raises(InvalidAccountError):
        Customer(1, name, email)


def test_deposit_increases_balance(any_account: Account) -> None:
    transaction = any_account.deposit(Money(250.25))
    assert any_account.balance.amount == pytest.approx(750.25)
    assert transaction.kind is TransactionType.DEPOSIT
    assert list(any_account) == [transaction]


def test_withdraw_decreases_balance(current_account: Account) -> None:
    current_account.withdraw(Money(400))
    assert current_account.balance == Money(600)


@pytest.mark.parametrize(
    ("amount", "allowed"),
    [
        pytest.param(999.99, True, id="below-balance"),
        pytest.param(1000.00, True, id="exactly-balance"),
        pytest.param(1000.01, False, id="one-cent-over"),
    ],
)
def test_withdraw_boundary(current_account: Account, amount: float, allowed: bool) -> None:
    if allowed:
        current_account.withdraw(Money(amount))
        assert current_account.balance.amount >= 0
    else:
        with pytest.raises(InsufficientFundsError):
            current_account.withdraw(Money(amount))
        assert current_account.balance == Money(1000)  # стан не змінився


def test_insufficient_funds_details(current_account: Account) -> None:
    with pytest.raises(InsufficientFundsError) as exc_info:
        current_account.withdraw(Money(5000))
    assert exc_info.value.account_number == "UA100001"
    assert exc_info.value.requested == "5 000.00 UAH"


def test_zero_amount_is_invalid(any_account: Account) -> None:
    with pytest.raises(InvalidAmountError, match="додатною"):
        any_account.deposit(Money(0))


def test_savings_keeps_minimum_balance(account_factory: Callable[..., Account]) -> None:
    savings = account_factory(kind="savings", balance=1000, minimum_balance=Money(300))
    assert savings.available_for_withdrawal() == Money(700)
    with pytest.raises(InsufficientFundsError):
        savings.withdraw(Money(700.01))


def test_savings_interest_and_invalid_rate(account_factory: Callable[..., Account],
                                           owner: Customer) -> None:
    savings = account_factory(kind="savings", balance=1000, interest_rate=0.05)
    transaction = savings.close_month()
    assert transaction is not None and transaction.amount == Money(50)
    assert savings.balance == Money(1050)
    with pytest.raises(InvalidAmountError):
        SavingsAccount("UA100009", owner, interest_rate=0.5)


def test_empty_savings_has_no_interest(account_factory: Callable[..., Account]) -> None:
    savings = account_factory(kind="savings", balance=0)
    assert savings.available_for_withdrawal() == Money(0)
    assert savings.close_month() is None


@pytest.mark.parametrize(("balance", "fee", "left"), [(100, 25, 75), (10, 10, 0), (0, 0, 0)])
def test_current_fee_never_makes_balance_negative(
        account_factory: Callable[..., Account], balance: float, fee: float, left: float) -> None:
    account = account_factory(balance=balance)
    transaction = account.close_month()
    assert account.balance == Money(left)
    assert (transaction is None) == (fee == 0)


def test_dunder_methods(account_factory: Callable[..., Account]) -> None:
    poor, rich = account_factory("UA100001", 10), account_factory("UA100002", 900)
    assert poor < rich and max([poor, rich]) is rich
    assert poor == account_factory("UA100001", 999) and poor != "UA100001"
    assert len({poor, rich}) == 2
    assert "UA100002" in repr(rich) and "current" in str(rich)


def test_transaction_text_representation(current_account: Account) -> None:
    transaction = current_account.withdraw(Money(100))
    assert str(transaction).endswith("UA100001 withdraw 100.00 UAH -> баланс 900.00 UAH")
