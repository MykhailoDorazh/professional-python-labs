from unittest.mock import AsyncMock

import pytest

from employee_app.exceptions import PayrollProviderError
from employee_app.gateway import AsyncPayrollService
from employee_app.models import Employee
from employee_app.repositories import InMemoryRepository
from employee_app.services import HRService
from employee_app.value_objects import Money


@pytest.fixture
def provider() -> AsyncMock:
    mock = AsyncMock()
    mock.get_bonus.return_value = 1_000.0
    return mock


@pytest.mark.asyncio
async def test_payroll_adds_kpi_bonus(staffed: HRService, employees: InMemoryRepository[Employee],
                                      provider: AsyncMock) -> None:
    service = AsyncPayrollService(employees, provider)
    records = await service.calculate("2026-11")
    assert [r.employee_id for r in records] == ["E0001", "E0002", "E0003"]
    assert records[0].bonus == Money(1_000)  # employee: only KPI
    assert records[1].bonus == Money(19_000)  # manager: 20 % + KPI
    assert service.total(records) == Money(170_000.5 + 18_000 + 3_000)
    assert provider.get_bonus.await_count == 3
    provider.get_bonus.assert_any_await("E0002", "2026-11")


@pytest.mark.asyncio
async def test_provider_failure_is_chained(staffed: HRService,
                                           employees: InMemoryRepository[Employee],
                                           provider: AsyncMock) -> None:
    provider.get_bonus.side_effect = [500.0, TimeoutError("KPI system timeout"), 0.0]
    with pytest.raises(PayrollProviderError, match="E0002") as exc_info:
        await AsyncPayrollService(employees, provider).calculate("2026-11")
    assert isinstance(exc_info.value.__cause__, TimeoutError)


@pytest.mark.asyncio
async def test_negative_bonus_rejected(hr: HRService, employees: InMemoryRepository[Employee],
                                       provider: AsyncMock) -> None:
    provider.get_bonus.return_value = -1.0
    with pytest.raises(PayrollProviderError, match="Negative"):
        await AsyncPayrollService(employees, provider).calculate("2026-11")


@pytest.mark.asyncio
async def test_empty_repository_needs_no_requests(employees: InMemoryRepository[Employee],
                                                  provider: AsyncMock) -> None:
    assert await AsyncPayrollService(employees, provider).calculate("2026-11") == []
    provider.get_bonus.assert_not_awaited()
