"""Experiments 1-2: the same calls with meaningful assertions."""

import pytest

from exp_code import apply_raise, withholding


def test_raise_strong() -> None:
    assert apply_raise(40_000, 10) == pytest.approx(44_000)


@pytest.mark.parametrize(("salary", "tax"), [(10_000, 1_950.0), (52_000, 10_140.0)])
def test_withholding_strong(salary: float, tax: float) -> None:
    assert withholding(salary) == pytest.approx(tax)
