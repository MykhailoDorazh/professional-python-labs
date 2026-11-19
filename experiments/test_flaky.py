"""Experiment 5: flaky test vs deterministic test."""

import random

import pytest

import exp_code


@pytest.mark.parametrize("run", range(10))
def test_random_bad(run: int) -> None:
    assert exp_code.lucky_bonus() == 1  # залежить від випадковості


@pytest.mark.parametrize("value", [1, 2])
def test_random_deterministic(monkeypatch: pytest.MonkeyPatch, value: int) -> None:
    monkeypatch.setattr(exp_code.random, "randint", lambda low, high: value)
    assert exp_code.lucky_bonus() == value


def test_seeded_random() -> None:
    random.seed(42)
    first = [exp_code.lucky_bonus() for _ in range(5)]
    random.seed(42)
    assert [exp_code.lucky_bonus() for _ in range(5)] == first
