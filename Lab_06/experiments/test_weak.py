"""Experiments 1-2: weak tests without assertions (execution != verification)."""

from exp_code import apply_raise, withholding


def test_raise_weak() -> None:
    apply_raise(40_000, 10)


def test_withholding_weak() -> None:
    withholding(10_000)
    withholding(52_000)
