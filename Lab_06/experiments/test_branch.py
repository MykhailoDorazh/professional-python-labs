"""Experiment 3: branch coverage. Run with -k partial, then without -k."""

import pytest

from exp_code import classify_balance


@pytest.mark.parametrize(("balance", "expected"), [(150_000, "vip"), (5_000, "standard")])
def test_partial(balance: float, expected: str) -> None:
    assert classify_balance(balance) == expected


def test_missing_branch() -> None:
    assert classify_balance(50) == "low"
