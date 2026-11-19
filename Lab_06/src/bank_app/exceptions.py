"""Custom exception hierarchy of the bank application."""


class BankError(Exception):
    """Base class for all application errors."""


class ValidationError(BankError):
    """Data of a domain object is invalid."""


class InvalidAmountError(ValidationError):
    """Amount of an operation must be positive."""


class InvalidAccountError(ValidationError):
    """Account number or owner data is invalid."""


class CurrencyMismatchError(BankError):
    """Operation mixes different currencies."""


class InsufficientFundsError(BankError):
    """Withdrawal would make the balance negative (or below the minimum)."""

    def __init__(self, account_number: str, requested: str, available: str) -> None:
        super().__init__(
            f"Недостатньо коштів на {account_number}: "
            f"доступно {available}, запит {requested}"
        )
        self.account_number = account_number
        self.requested = requested
        self.available = available


class AccountNotFoundError(BankError):
    """No account with the given number."""


class DuplicateAccountError(BankError):
    """Account with the same number already exists."""


class ConfigurationError(BankError):
    """Configuration is missing or invalid."""


class DataImportError(BankError):
    """Input file cannot be read."""


class RecordValidationError(BankError):
    """One input record is invalid."""

    def __init__(self, message: str, *, line_number: int | None = None,
                 field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field


class DataExportError(BankError):
    """Output cannot be written."""


class GatewayError(BankError):
    """External banking system failed."""
