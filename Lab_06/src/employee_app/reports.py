"""Report abstraction (ABC) and the report service that publishes reports."""

import json
from abc import ABC, abstractmethod
from typing import Protocol

from employee_app.models import PayrollRecord
from employee_app.services import PayrollService


class ReportFormatter(ABC):
    """Abstract report: the order of sections is fixed, the format is not."""

    def render(self, period: str, records: list[PayrollRecord],
               departments: dict[str, dict[str, float]]) -> str:
        return "\n".join([self.header(period), self.body(records, departments)])

    @abstractmethod
    def header(self, period: str) -> str: ...

    @abstractmethod
    def body(self, records: list[PayrollRecord],
             departments: dict[str, dict[str, float]]) -> str: ...


class TextReport(ReportFormatter):
    def header(self, period: str) -> str:
        return f"Відомість нарахувань за {period}"

    def body(self, records: list[PayrollRecord],
             departments: dict[str, dict[str, float]]) -> str:
        lines = [f"  {r.employee_id}: оклад {r.base.amount:.2f} + премія {r.bonus.amount:.2f} "
                 f"= {r.total.amount:.2f}" for r in records]
        lines += [f"  {code}: {int(s['employees'])} осіб, фонд {s['payroll']:.2f}, "
                  f"середня {s['average']:.2f}" for code, s in departments.items()]
        return "\n".join(lines)


class JsonReport(ReportFormatter):
    def header(self, period: str) -> str:
        return json.dumps({"report": "payroll", "period": period})

    def body(self, records: list[PayrollRecord],
             departments: dict[str, dict[str, float]]) -> str:
        return json.dumps({"total": round(sum(r.total.amount for r in records), 2),
                           "records": len(records), "departments": departments},
                          ensure_ascii=False)


class ReportPublisher(Protocol):
    """Where a finished report goes: file, e-mail, document storage."""

    def publish(self, name: str, content: str) -> None: ...


class ReportService:
    """Builds the payroll report for a period and hands it to the publisher."""

    def __init__(self, payroll: PayrollService, formatter: ReportFormatter,
                 publisher: ReportPublisher) -> None:
        self._payroll = payroll
        self._formatter = formatter
        self._publisher = publisher

    def publish_payroll(self, period: str, records: list[PayrollRecord] | None = None) -> str:
        records = self._payroll.run_payroll(period) if records is None else records
        content = self._formatter.render(period, records, self._payroll.by_department())
        self._publisher.publish(f"payroll_{period}", content)
        return content
