import pytest

from employee_app.exceptions import CurrencyMismatchError, InvalidEmployeeError
from employee_app.value_objects import EmployeeId, Money


def test_money_creation_rounds_to_cents() -> None:
    money = Money(10.005 + 0.001, "UAH")
    assert money.amount == pytest.approx(10.01)
    assert money.currency == "UAH"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        pytest.param(0, 0.0, id="zero"),
        pytest.param(0.01, 0.01, id="one-cent"),
        pytest.param(52_000, 52_000.0, id="normal"),
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
    assert Money(90) / 4 == Money(22.5)
    assert Money(10) < Money(20)
    assert not Money(0)


def test_currency_mismatch_is_custom_exception() -> None:
    with pytest.raises(CurrencyMismatchError, match="UAH != USD"):
        Money(1, "UAH") + Money(1, "USD")


@pytest.mark.parametrize("value", ["e1234", " E0001 "])
def test_employee_id_normalized(value: str) -> None:
    employee_id = EmployeeId(value)
    assert str(employee_id) == value.strip().upper()


@pytest.mark.parametrize("value", ["", "E123", "E12345", "X1234", "E12a4"])
def test_invalid_employee_ids(value: str) -> None:
    with pytest.raises(InvalidEmployeeError):
        EmployeeId(value)
