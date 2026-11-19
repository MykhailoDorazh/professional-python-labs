"""Experiment 3: branch coverage. Run with -k partial, then without -k."""

import pytest

from exp_code import classify_salary


@pytest.mark.parametrize(("salary", "expected"), [(150_000, "high"), (52_000, "medium")])
def test_partial(salary: float, expected: str) -> None:
    assert classify_salary(salary) == expected


def test_missing_branch() -> None:
    assert classify_salary(8_000) == "low"
