"""Asynchronous external dependency: payroll provider (KPI bonuses)."""

import asyncio
from typing import Protocol

from employee_app.exceptions import PayrollProviderError
from employee_app.models import PayrollRecord
from employee_app.protocols import EmployeeReader
from employee_app.value_objects import Money


class PayrollProvider(Protocol):
    """External system that returns the KPI bonus of an employee for a period."""

    async def get_bonus(self, employee_id: str, period: str) -> float: ...


class AsyncPayrollService:
    """Calculates payroll: base salary + role bonus + KPI bonus from the provider.
    Bonuses of all employees are requested concurrently (asyncio.gather)."""

    def __init__(self, employees: EmployeeReader, provider: PayrollProvider) -> None:
        self._employees = employees
        self._provider = provider

    async def _kpi_bonus(self, employee_id: str, period: str) -> float:
        try:
            value = await self._provider.get_bonus(employee_id, period)
        except Exception as error:
            raise PayrollProviderError(f"Bonus for {employee_id} is unavailable") from error
        if value < 0:
            raise PayrollProviderError(f"Negative bonus {value} for {employee_id}")
        return value

    async def calculate(self, period: str) -> list[PayrollRecord]:
        employees = list(self._employees)
        if not employees:
            return []
        bonuses = await asyncio.gather(*(self._kpi_bonus(e.employee_id, period)
                                         for e in employees))
        return [PayrollRecord(number, e.employee_id, period, e.salary,
                              e.bonus() + Money(kpi, e.salary.currency))
                for number, (e, kpi) in enumerate(zip(employees, bonuses, strict=True), 1)]

    @staticmethod
    def total(records: list[PayrollRecord]) -> Money:
        return sum((r.total for r in records), start=Money.zero())
