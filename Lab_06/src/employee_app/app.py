"""Integration flow: CSV import -> departments -> statistics -> JSON + report."""

import logging
from dataclasses import dataclass
from pathlib import Path

from employee_app.config import AppConfig
from employee_app.exceptions import DuplicateEmployeeError
from employee_app.exporter import FileReportPublisher, export_employees_json
from employee_app.importer import ImportStatistics, read_employees
from employee_app.models import Department, Employee
from employee_app.protocols import Notifier
from employee_app.reports import ReportService, TextReport
from employee_app.repositories import InMemoryRepository
from employee_app.services import HRService, PayrollService

logger = logging.getLogger(__name__)


@dataclass
class FlowResult:
    employees: int
    invalid: int
    rejected: int
    exported: int
    payroll: float
    average: float
    highest: str | None


def build_services(config: AppConfig, notifier: Notifier
                   ) -> tuple[HRService, PayrollService, InMemoryRepository[Employee]]:
    employees: InMemoryRepository[Employee] = InMemoryRepository()
    departments: InMemoryRepository[Department] = InMemoryRepository()
    for code, name in config.departments.items():
        departments.add(Department(code, name))
    return HRService(employees, departments, notifier), PayrollService(employees), employees


def run_flow(employees_csv: Path, output_dir: Path, config: AppConfig, notifier: Notifier,
             period: str = "2026-11") -> FlowResult:
    hr, payroll, repository = build_services(config, notifier)
    statistics = ImportStatistics()
    rejected = 0
    for record in read_employees(employees_csv, config, statistics):
        try:
            hr.add_employee(record.employee, record.department)
        except DuplicateEmployeeError as error:
            rejected += 1
            logger.warning("Line %s rejected: %s", record.line_number, error)

    exported = export_employees_json(repository, output_dir / "employees.json")
    ReportService(payroll, TextReport(), FileReportPublisher(output_dir)).publish_payroll(period)
    top = payroll.highest_paid()
    return FlowResult(len(repository), statistics.invalid, rejected, exported,
                      payroll.total_payroll().amount, payroll.average_salary().amount,
                      top.employee_id if top else None)
