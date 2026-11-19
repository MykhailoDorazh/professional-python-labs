"""Whole application (main) and async account operation flow."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from bank_app import main as main_module
from bank_app.exceptions import GatewayError
from bank_app.gateway import AsyncPayoutService
from bank_app.importer import import_accounts
from bank_app.models import Account
from bank_app.repositories import InMemoryRepository
from bank_app.services import BankService, ReportService
from bank_app.value_objects import Money

pytestmark = pytest.mark.integration


def test_main_end_to_end(project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main_module.main()
    out = capsys.readouterr().out
    assert "applied=3, rejected=2, invalid=2" in out
    assert "переказ TRX-001-400, залишок 600.00 UAH" in out
    assert json.loads((project_dir / "output/accounts.json").read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_async_account_operation_flow(project_dir: Path, notifier: Mock) -> None:
    repository: InMemoryRepository[Account] = InMemoryRepository()
    bank = BankService(repository, notifier)
    for account in import_accounts(project_dir / "data/accounts.csv"):
        bank.open_account(account)

    gateway = AsyncMock()
    gateway.send_transfer.side_effect = ["TRX-1", ConnectionError("timeout")]
    service = AsyncPayoutService(bank, gateway)

    assert await service.payout("UA100001", Money(10_000)) == "TRX-1"
    with pytest.raises(GatewayError):
        await service.payout("UA100003", Money(500))

    assert bank.get_balance("UA100001") == Money(40_000)
    assert bank.get_balance("UA100003") == Money(12_750.5)  # повернено після збою
    assert ReportService(repository).total_funds() == Money(55_950.5)
    assert gateway.send_transfer.await_count == 2
