"""Money helpers: salaries are stored in the database as integer cents (копійки)."""

from decimal import Decimal, InvalidOperation

from employee_db.exceptions import InvalidSalaryError

MAX_SALARY_CENTS = 100_000_000  # 1 000 000.00 грн, той самий ліміт, що й CHECK у БД


def to_cents(amount: Decimal | str | int) -> int:
    """Convert a salary in UAH to integer cents (0 is allowed).

    Raises:
        InvalidSalaryError: amount is not a number, is negative
            or has more than two decimal places.
    """
    try:
        value = Decimal(str(amount))
    except InvalidOperation as error:
        raise InvalidSalaryError(f"Некоректна сума: {amount!r}") from error
    if not value.is_finite() or value < 0:
        raise InvalidSalaryError(f"Зарплата не може бути від'ємною: {amount}")
    cents = value * 100
    if cents != cents.to_integral_value():
        raise InvalidSalaryError(f"Не більше двох знаків після коми: {amount}")
    return int(cents)


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))


def fmt(cents: int | float) -> str:
    """12345678 -> '123 456.78'."""
    return f"{Decimal(cents) / 100:,.2f}".replace(",", " ")
