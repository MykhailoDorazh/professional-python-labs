"""Records that travel through the pipeline (immutable NamedTuples)."""

from typing import NamedTuple

EMPLOYEE_ID_PATTERN = r"E\d{6}"
MAX_SALARY = 1_000_000.0


class Employee(NamedTuple):
    """Validated employee record."""

    employee_id: str
    name: str
    position: str
    department: str
    salary: float
