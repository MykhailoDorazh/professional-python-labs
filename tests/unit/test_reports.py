import json
from unittest.mock import Mock, create_autospec

import pytest

from employee_app.models import PayrollRecord
from employee_app.reports import (
    JsonReport,
    ReportFormatter,
    ReportPublisher,
    ReportService,
    TextReport,
)
from employee_app.services import HRService, PayrollService
from employee_app.value_objects import Money

RECORDS = [PayrollRecord(1, "E0001", "2026-11", Money(50_000), Money(0)),
           PayrollRecord(2, "E0002", "2026-11", Money(90_000), Money(18_000))]
DEPARTMENTS = {"IT": {"employees": 2, "payroll": 140_000.0, "average": 70_000.0}}


@pytest.fixture
def publisher() -> Mock:
    return create_autospec(ReportPublisher, instance=True)


def test_abstract_formatter_cannot_be_created() -> None:
    with pytest.raises(TypeError):
        ReportFormatter()  # type: ignore[abstract]


def test_text_report() -> None:
    text = TextReport().render("2026-11", RECORDS, DEPARTMENTS)
    assert text.splitlines()[0] == "Відомість нарахувань за 2026-11"
    assert "E0002: оклад 90000.00 + премія 18000.00 = 108000.00" in text
    assert "IT: 2 осіб, фонд 140000.00, середня 70000.00" in text


def test_json_report() -> None:
    header, body = JsonReport().render("2026-11", RECORDS, DEPARTMENTS).splitlines()
    assert json.loads(header) == {"report": "payroll", "period": "2026-11"}
    assert json.loads(body)["total"] == 158_000.0


def test_report_service_publishes_through_mock(staffed: HRService, payroll: PayrollService,
                                               publisher: Mock) -> None:
    content = ReportService(payroll, TextReport(), publisher).publish_payroll("2026-11")
    publisher.publish.assert_called_once_with("payroll_2026-11", content)
    assert "E0003" in content and "FIN: 1 осіб" in content


def test_report_service_uses_given_records_and_formatter(payroll: PayrollService,
                                                         publisher: Mock) -> None:
    formatter = Mock(spec=ReportFormatter)
    formatter.render.return_value = "REPORT"
    service = ReportService(payroll, formatter, publisher)
    assert service.publish_payroll("2026-12", RECORDS) == "REPORT"
    formatter.render.assert_called_once_with("2026-12", RECORDS, {})
    publisher.publish.assert_called_once_with("payroll_2026-12", "REPORT")


def test_publisher_error_propagates(payroll: PayrollService, publisher: Mock) -> None:
    publisher.publish.side_effect = OSError("storage is down")
    with pytest.raises(OSError, match="storage"):
        ReportService(payroll, TextReport(), publisher).publish_payroll("2026-11")
