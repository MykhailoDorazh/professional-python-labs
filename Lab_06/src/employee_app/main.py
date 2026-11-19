"""Demo: integration flow + async payroll with an external bonus provider."""

import asyncio
import logging
from pathlib import Path

from employee_app.app import run_flow
from employee_app.config import load_config
from employee_app.gateway import AsyncPayrollService
from employee_app.models import Developer, Employee, Manager
from employee_app.repositories import InMemoryRepository
from employee_app.services import ConsoleNotifier
from employee_app.value_objects import Money


class DemoBonusProvider:
    """Stand-in for the KPI system: answers after a short network delay."""

    async def get_bonus(self, employee_id: str, period: str) -> float:
        await asyncio.sleep(0.01)
        return 1_000.0 if employee_id.endswith("1") else 0.0


async def demo_payroll() -> None:
    employees = InMemoryRepository[Employee]()
    employees.add(Manager("E2001", "Тарас Новак", "Керівник", Money(80_000), bonus_rate=0.1))
    employees.add(Developer("E2002", "Ірина Кравець", "Розробник", Money(60_000), level="junior"))
    service = AsyncPayrollService(employees, DemoBonusProvider())
    records = await service.calculate("2026-11")
    for record in records:
        print(f"   {record}")
    print(f"   разом до виплати: {service.total(records)}")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
    config = load_config(Path("config.yaml"))
    print("1. Потік CSV -> відділи -> статистика -> JSON + звіт:")
    result = run_flow(Path("data/employees.csv"), Path("output"), config, ConsoleNotifier())
    print(f"   {result}")
    print("2. Асинхронне нарахування з KPI-премією від зовнішньої системи:")
    asyncio.run(demo_payroll())


if __name__ == "__main__":
    main()
