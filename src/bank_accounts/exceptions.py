"""Custom exceptions of the bank accounts system."""


class BankError(Exception):
    """Base class for all errors of the application."""


class InvalidAmountError(BankError):
    """Amount of an operation is not a positive number or is too big."""


class InsufficientFundsError(BankError):
    """Withdrawal would make the balance negative."""


class AccountNotFoundError(BankError):
    """Account with the given number does not exist."""


class InvalidAccountError(BankError):
    """Account data (number, client name, balance) is invalid."""
