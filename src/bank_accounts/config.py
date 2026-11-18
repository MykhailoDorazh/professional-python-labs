"""Configuration constants of the application."""

CURRENCY: str = "грн"

# Мінімально допустимий баланс рахунку: від'ємний баланс заборонено.
MIN_BALANCE: float = 0.0

# Номер рахунку: "UA" + 6 цифр, наприклад UA100001.
ACCOUNT_NUMBER_PATTERN: str = r"UA\d{6}"

# Максимальна сума однієї операції.
MAX_OPERATION_AMOUNT: float = 1_000_000.0
