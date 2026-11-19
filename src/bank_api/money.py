"""Money helpers: amounts are stored in the database as integer cents (копійки)."""

from decimal import Decimal, InvalidOperation

from bank_api.exceptions import InvalidAmountError


def to_cents(amount: Decimal | str | int) -> int:
    """Convert a positive amount in UAH to integer cents.

    Raises:
        InvalidAmountError: amount is not a number, is not positive
            or has more than two decimal places.
    """
    try:
        value = Decimal(str(amount))
    except InvalidOperation as error:
        raise InvalidAmountError(f"Некоректна сума: {amount!r}") from error
    if not value.is_finite() or value <= 0:
        raise InvalidAmountError(f"Сума має бути додатною: {amount}")
    cents = value * 100
    if cents != cents.to_integral_value():
        raise InvalidAmountError(f"Не більше двох знаків після коми: {amount}")
    return int(cents)


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))


def fmt(cents: int) -> str:
    """12345678 -> '123 456.78'."""
    return f"{from_cents(cents):,.2f}".replace(",", " ")
