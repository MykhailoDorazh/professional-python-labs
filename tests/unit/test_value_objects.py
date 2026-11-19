import pytest

from bank_app.exceptions import CurrencyMismatchError, InvalidAccountError
from bank_app.value_objects import AccountNumber, Money


def test_money_creation_rounds_to_cents() -> None:
    money = Money(10.005 + 0.001, "UAH")
    assert money.amount == pytest.approx(10.01)
    assert money.currency == "UAH"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        pytest.param(0, 0.0, id="zero"),
        pytest.param(0.01, 0.01, id="one-cent"),
        pytest.param(100, 100.0, id="normal"),
        pytest.param(9_999_999.99, 9_999_999.99, id="large"),
    ],
)
def test_valid_money_amounts(amount: float, expected: float) -> None:
    assert Money(amount).amount == pytest.approx(expected)


def test_negative_money_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        Money(-0.01)


def test_money_arithmetic_and_ordering() -> None:
    assert Money(100) + Money(50.5) == Money(150.5)
    assert Money(100) - Money(0.1) == Money(99.9)
    assert Money(10) * 1.5 == Money(15)
    assert Money(10) < Money(20)
    assert not Money(0)


def test_currency_mismatch_is_custom_exception() -> None:
    with pytest.raises(CurrencyMismatchError, match="UAH != USD"):
        Money(1, "UAH") + Money(1, "USD")


@pytest.mark.parametrize("value", ["ua123456", " UA000001 "])
def test_account_number_normalized(value: str) -> None:
    number = AccountNumber(value)
    assert str(number).startswith("UA")
    assert number.masked == f"UA****{number.value[-2:]}"


@pytest.mark.parametrize("value", ["", "UA12345", "UA1234567", "XX123456", "UA12345a"])
def test_invalid_account_numbers(value: str) -> None:
    with pytest.raises(InvalidAccountError):
        AccountNumber(value)
