"""Demo: integration flow + async payout."""

import asyncio
import logging
from pathlib import Path

from bank_app.app import run_flow
from bank_app.config import load_config
from bank_app.gateway import AsyncPayoutService
from bank_app.models import CurrentAccount, Customer
from bank_app.repositories import InMemoryRepository
from bank_app.services import BankService, ConsoleNotifier
from bank_app.value_objects import Money


class DemoGateway:
    async def send_transfer(self, account_number: str, amount: Money) -> str:
        await asyncio.sleep(0.01)
        return f"TRX-{account_number[-3:]}-{int(amount.amount)}"


async def demo_payout() -> None:
    bank = BankService(InMemoryRepository(), ConsoleNotifier())
    bank.open_account(CurrentAccount("UA200001", Customer(3, "Тарас Новак", "taras@example.com"),
                                     Money(1_000)))
    reference = await AsyncPayoutService(bank, DemoGateway()).payout("UA200001", Money(400))
    print(f"   переказ {reference}, залишок {bank.get_balance('UA200001')}")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
    config = load_config(Path("config.yaml"))
    print("1. Потік імпорт -> операції -> експорт:")
    result = run_flow(Path("data/accounts.csv"), Path("data/operations.csv"),
                      Path("output/accounts.json"), config, ConsoleNotifier())
    print(f"   {result}")
    print("2. Асинхронний переказ через зовнішній шлюз:")
    asyncio.run(demo_payout())


if __name__ == "__main__":
    main()
