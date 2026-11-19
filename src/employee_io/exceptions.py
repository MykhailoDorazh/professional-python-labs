"""Custom exception hierarchy of the application.

ApplicationError
├── ConfigurationError
└── DataError
    ├── DataImportError
    ├── RecordValidationError
    │   └── SalaryValidationError
    └── DataExportError
"""


class ApplicationError(Exception):
    """Base application exception."""


class ConfigurationError(ApplicationError):
    """Configuration file is missing or invalid."""


class DataError(ApplicationError):
    """Base data exception."""


class DataImportError(DataError):
    """Input data cannot be read."""


class RecordValidationError(DataError):
    """One input record is invalid. Carries the line and the field."""

    def __init__(self, message: str, *, line_number: int | None = None,
                 field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field


class SalaryValidationError(RecordValidationError):
    """Salary is not a number or is outside the allowed range.
    The message never contains the salary value itself (confidential data)."""


class DataExportError(DataError):
    """Output cannot be written."""
