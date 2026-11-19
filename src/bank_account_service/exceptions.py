"""Domain exceptions of the bank persistence layer."""


class BankError(Exception):
    """Base class for all business errors of the application."""


class InvalidAmountError(BankError):
    """Amount of money is zero, negative or has more than two decimal places."""


class InsufficientFundsError(BankError):
    """Withdrawal or transfer would make the balance negative."""


class AccountNotFoundError(BankError):
    """There is no account with the given id or number."""


class ClientNotFoundError(BankError):
    """There is no client with the given id."""


class DuplicateAccountError(BankError):
    """Account number must be unique (UNIQUE constraint)."""


class AccountNotEmptyError(BankError):
    """Account with a positive balance cannot be closed."""
