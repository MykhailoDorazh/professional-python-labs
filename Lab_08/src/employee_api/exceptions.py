"""Domain exceptions of the employee persistence layer."""


class HRError(Exception):
    """Base class for all business errors of the application."""


class InvalidSalaryError(HRError):
    """Salary is not a number, is negative, exceeds the maximum or has > 2 decimals."""


class EmployeeNotFoundError(HRError):
    """There is no employee with the given personnel number."""


class DepartmentNotFoundError(HRError):
    """There is no department with the given code."""


class DuplicateEmployeeError(HRError):
    """Personnel number must be unique (UNIQUE constraint)."""


class DuplicateDepartmentError(HRError):
    """Department code must be unique (UNIQUE constraint)."""


class DepartmentNotEmptyError(HRError):
    """Department that still has employees cannot be deleted (FOREIGN KEY RESTRICT)."""
