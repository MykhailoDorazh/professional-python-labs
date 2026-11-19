"""Code for the testing experiments (contains INTENTIONAL defects)."""

import random


def apply_interest(balance: float, rate: float) -> float:
    """Should return balance + interest. DEFECT: returns only the interest."""
    return round(balance * rate, 2)


def withdrawal_fee(amount: float) -> float:
    """Should be 1 % but at least 5. DEFECT: uses max of wrong values."""
    return max(amount * 0.1, 5.0)


def classify_balance(balance: float) -> str:
    if balance >= 100_000:
        return "vip"
    if balance >= 1_000:
        return "standard"
    return "low"


def lucky_bonus() -> int:
    """Random bonus: 1 or 2."""
    return random.randint(1, 2)


class FakeRepository:
    """Fake: a real, simplified implementation that keeps state."""

    def __init__(self) -> None:
        self.items: dict[str, float] = {}

    def add(self, number: str, balance: float) -> None:
        self.items[number] = balance

    def get(self, number: str) -> float | None:
        return self.items.get(number)


def total_of(repository: FakeRepository, numbers: list[str]) -> float:
    return sum(repository.get(n) or 0.0 for n in numbers)
