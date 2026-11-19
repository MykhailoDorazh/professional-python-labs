"""Code for the testing experiments (contains INTENTIONAL defects)."""

import random


def apply_raise(salary: float, percent: float) -> float:
    """Should return the new salary. DEFECT: returns only the raise itself."""
    return round(salary * percent / 100, 2)


def withholding(salary: float) -> float:
    """Should be 19.5 % (18 % PDFO + 1.5 % military levy). DEFECT: only 18 %."""
    return round(salary * 0.18, 2)


def classify_salary(salary: float) -> str:
    if salary >= 100_000:
        return "high"
    if salary >= 20_000:
        return "medium"
    return "low"


def lucky_bonus() -> int:
    """Random bonus multiplier: 1 or 2."""
    return random.randint(1, 2)


class FakeRepository:
    """Fake: a real, simplified implementation that keeps state."""

    def __init__(self) -> None:
        self.items: dict[str, float] = {}

    def add(self, employee_id: str, salary: float) -> None:
        self.items[employee_id] = salary

    def get(self, employee_id: str) -> float | None:
        return self.items.get(employee_id)


def payroll_of(repository: FakeRepository, employee_ids: list[str]) -> float:
    return sum(repository.get(e) or 0.0 for e in employee_ids)
