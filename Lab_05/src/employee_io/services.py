"""Import service: strict/tolerant processing, salary filter and statistics."""

import logging
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field

from employee_io.exceptions import RecordValidationError
from employee_io.models import AppConfig, Employee
from employee_io.readers import get_importer
from employee_io.utils import mask_id, mask_name, salary_band
from employee_io.validators import parse_employee

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    filtered: int = 0          # валідні, але зарплата < min_salary
    exported: int = 0
    payroll: float = 0.0       # фонд оплати праці експортованих працівників
    by_department: Counter[str] = field(default_factory=Counter)
    reasons: Counter[str] = field(default_factory=Counter)
    errors: list[tuple[int, str, str]] = field(default_factory=list)

    @property
    def average_salary(self) -> float:
        passed = sum(self.by_department.values())
        return round(self.payroll / passed, 2) if passed else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total, "valid": self.valid, "invalid": self.invalid,
            "filtered_by_min_salary": self.filtered, "exported": self.exported,
            "payroll": round(self.payroll, 2), "average_salary": self.average_salary,
            "employees_by_department": dict(self.by_department),
            "invalid_by_field": dict(self.reasons),
        }


def import_employees(config: AppConfig, statistics: ImportStatistics) -> Iterator[Employee]:
    """Streaming import: valid employees with salary >= min_salary, one by one.

    Tolerant mode (skip_invalid=true): invalid record -> warning, counter, skip.
    Strict mode (skip_invalid=false): the first invalid record stops the import.
    """
    importer = get_importer(config.input_path)
    min_salary = config.processing.min_salary
    for line_number, row in importer.read(config.input_path):
        statistics.total += 1
        try:
            employee = parse_employee(row, line_number=line_number, config=config.processing)
        except RecordValidationError as error:
            statistics.invalid += 1
            statistics.reasons[error.field or "unknown"] += 1
            statistics.errors.append((line_number, error.field or "", str(error)))
            # у лог - лише маскований номер, без ПІБ і без зарплати
            logger.warning("Invalid record at line %s (%s): %s [field=%s]", line_number,
                           mask_id(row.get("employee_id") or ""), error, error.field)
            if config.processing.skip_invalid:
                continue
            raise
        statistics.valid += 1
        if employee.salary < min_salary:
            statistics.filtered += 1
            logger.info("Filtered %s (%s): salary below min_salary", mask_id(employee.employee_id),
                        mask_name(employee.name))
            continue
        statistics.payroll += employee.salary
        statistics.by_department[employee.department] += 1
        logger.debug("Accepted %s, department %s, salary band %s", mask_id(employee.employee_id),
                     employee.department, salary_band(employee.salary))
        yield employee
