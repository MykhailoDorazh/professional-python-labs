"""Asynchronous external dependencies: interbank gateway and exchange rates."""

from typing import Protocol

from bank_app.exceptions import GatewayError
from bank_app.services import BankService
from bank_app.value_objects import Money


class ExternalBankGateway(Protocol):
    async def send_transfer(self, account_number: str, amount: Money) -> str: ...


class ExchangeRateProvider(Protocol):
    async def get_rate(self, base: str, target: str) -> float: ...


class AsyncPayoutService:
    """Withdraws money and sends it to another bank. If the external gateway
    fails, the withdrawal is compensated (money is returned to the account)."""

    def __init__(self, bank: BankService, gateway: ExternalBankGateway) -> None:
        self._bank = bank
        self._gateway = gateway

    async def payout(self, account_number: str, amount: Money) -> str:
        self._bank.withdraw(account_number, amount)
        try:
            return await self._gateway.send_transfer(account_number, amount)
        except Exception as error:
            self._bank.deposit(account_number, amount)  # компенсація
            raise GatewayError(f"Transfer from {account_number} failed") from error


class CurrencyConverter:
    def __init__(self, provider: ExchangeRateProvider) -> None:
        self._provider = provider

    async def convert(self, money: Money, target: str) -> Money:
        if money.currency == target:
            return money
        rate = await self._provider.get_rate(money.currency, target)
        if rate <= 0:
            raise GatewayError(f"Invalid exchange rate {rate}")
        return Money(money.amount * rate, target)
