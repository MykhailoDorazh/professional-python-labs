"""Custom exceptions of the employee management system."""


class EmployeeError(Exception):
    """Base class for all errors of the application."""


class InvalidEmployeeError(EmployeeError):
    """Employee data (id, name, position, department) is invalid."""


class InvalidSalaryError(EmployeeError):
    """Salary is negative, too big or not a number."""


class EmployeeNotFoundError(EmployeeError):
    """Employee with the given id does not exist."""
