from unittest.mock import AsyncMock

import pytest

from bank_app.exceptions import GatewayError, InsufficientFundsError
from bank_app.gateway import AsyncPayoutService, CurrencyConverter
from bank_app.services import BankService
from bank_app.value_objects import Money


@pytest.mark.asyncio
async def test_payout_success(bank: BankService) -> None:
    gateway = AsyncMock()
    gateway.send_transfer.return_value = "TRX-001"
    reference = await AsyncPayoutService(bank, gateway).payout("UA100001", Money(300))
    assert reference == "TRX-001"
    assert bank.get_balance("UA100001") == Money(700)
    gateway.send_transfer.assert_awaited_once_with("UA100001", Money(300))


@pytest.mark.asyncio
async def test_payout_gateway_failure_restores_balance(bank: BankService) -> None:
    gateway = AsyncMock()
    gateway.send_transfer.side_effect = ConnectionError("Network error")
    with pytest.raises(GatewayError) as exc_info:
        await AsyncPayoutService(bank, gateway).payout("UA100001", Money(300))
    assert isinstance(exc_info.value.__cause__, ConnectionError)
    assert bank.get_balance("UA100001") == Money(1000)  # компенсація спрацювала


@pytest.mark.asyncio
async def test_payout_without_money_never_calls_gateway(bank: BankService) -> None:
    gateway = AsyncMock()
    with pytest.raises(InsufficientFundsError):
        await AsyncPayoutService(bank, gateway).payout("UA100001", Money(5000))
    gateway.send_transfer.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("rate", "expected"), [(0.024, 24.0), (1.0, 1000.0)])
async def test_currency_conversion(rate: float, expected: float) -> None:
    provider = AsyncMock()
    provider.get_rate.return_value = rate
    result = await CurrencyConverter(provider).convert(Money(1000), "USD")
    assert result.amount == pytest.approx(expected) and result.currency == "USD"
    provider.get_rate.assert_awaited_once_with("UAH", "USD")


@pytest.mark.asyncio
async def test_same_currency_needs_no_request() -> None:
    provider = AsyncMock()
    assert await CurrencyConverter(provider).convert(Money(5), "UAH") == Money(5)
    provider.get_rate.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_rate_rejected() -> None:
    provider = AsyncMock()
    provider.get_rate.return_value = 0
    with pytest.raises(GatewayError, match="rate"):
        await CurrencyConverter(provider).convert(Money(5), "EUR")
