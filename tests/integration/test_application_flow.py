"""Whole application (main) and async employee -> payroll -> report flow."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from employee_app import main as main_module
from employee_app.app import build_services
from employee_app.config import load_config
from employee_app.exporter import FileReportPublisher
from employee_app.gateway import AsyncPayrollService
from employee_app.importer import ImportStatistics, read_employees
from employee_app.reports import JsonReport, ReportService
from employee_app.value_objects import Money

pytestmark = pytest.mark.integration


def test_main_end_to_end(project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main_module.main()
    out = capsys.readouterr().out
    assert "employees=4, invalid=3, rejected=1, exported=4" in out
    assert "разом до виплати: 152 000.00 UAH" in out
    assert json.loads((project_dir / "output/employees.json").read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_async_employee_payroll_report_flow(project_dir: Path, notifier: Mock) -> None:
    config = load_config(project_dir / "config.yaml")
    hr, payroll, employees = build_services(config, notifier)
    for record in read_employees(project_dir / "data/employees.csv", config, ImportStatistics()):
        if record.employee.employee_id not in employees:
            hr.add_employee(record.employee, record.department)
    hr.transfer("E0003", "IT")

    provider = AsyncMock()
    provider.get_bonus.side_effect = lambda employee_id, period: 2_000.0 \
        if employee_id == "E0002" else 0.0
    records = await AsyncPayrollService(employees, provider).calculate("2026-11")

    content = ReportService(payroll, JsonReport(), FileReportPublisher(project_dir / "reports")
                            ).publish_payroll("2026-11", records)
    body = json.loads(content.splitlines()[1])
    assert body["records"] == 4
    assert body["total"] == pytest.approx(251_800 + 19_000 + 9_200 + 9_600)
    assert body["departments"]["IT"]["employees"] == 3
    assert AsyncPayrollService.total(records) == Money(body["total"])
    assert (project_dir / "reports/payroll_2026-11.txt").exists()
    assert provider.get_bonus.await_count == 4
