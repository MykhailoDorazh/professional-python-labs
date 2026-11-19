"""Experiments 1-2: weak tests without assertions (execution != verification)."""

from exp_code import apply_interest, withdrawal_fee


def test_interest_weak() -> None:
    apply_interest(1000, 0.05)


def test_fee_weak() -> None:
    withdrawal_fee(100)
    withdrawal_fee(1000)
