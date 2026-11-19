"""Experiments 1-2: the same calls with meaningful assertions."""

import pytest

from exp_code import apply_interest, withdrawal_fee


def test_interest_strong() -> None:
    assert apply_interest(1000, 0.05) == pytest.approx(1050)


@pytest.mark.parametrize(("amount", "fee"), [(100, 5.0), (1000, 10.0)])
def test_fee_strong(amount: float, fee: float) -> None:
    assert withdrawal_fee(amount) == pytest.approx(fee)
