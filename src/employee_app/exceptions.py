"""Custom exception hierarchy of the employee application."""


class EmployeeError(Exception):
    """Base class for all application errors."""


class ValidationError(EmployeeError):
    """Data of a domain object is invalid."""


class InvalidEmployeeError(ValidationError):
    """Employee id, name or position is invalid."""


class InvalidSalaryError(ValidationError):
    """Salary is outside the allowed range."""

    def __init__(self, value: float, low: float, high: float) -> None:
        super().__init__(f"Зарплата {value} поза межами {low:g}..{high:.10g}")
        self.value = value


class CurrencyMismatchError(EmployeeError):
    """Operation mixes different currencies."""


class EmployeeNotFoundError(EmployeeError):
    """No employee with the given id."""


class DepartmentNotFoundError(EmployeeError):
    """No department with the given code."""


class DuplicateEmployeeError(EmployeeError):
    """Employee with the same id already exists."""


class ConfigurationError(EmployeeError):
    """Configuration is missing or invalid."""


class DataImportError(EmployeeError):
    """Input file cannot be read."""


class RecordValidationError(EmployeeError):
    """One input record is invalid."""

    def __init__(self, message: str, *, line_number: int | None = None,
                 field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field


class DataExportError(EmployeeError):
    """Output cannot be written."""


class PayrollProviderError(EmployeeError):
    """External payroll (bonus) system failed."""
