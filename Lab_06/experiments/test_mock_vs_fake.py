"""Experiment 4: Mock vs Fake for the same function."""

from unittest.mock import Mock

from exp_code import FakeRepository, payroll_of


def test_payroll_with_mock() -> None:
    repository = Mock()
    repository.get.side_effect = lambda e: {"E0001": 50_000.0, "E0002": 30_000.0}.get(e)
    assert payroll_of(repository, ["E0001", "E0002", "E0003"]) == 80_000.0
    assert repository.get.call_count == 3  # interaction testing


def test_payroll_with_fake() -> None:
    repository = FakeRepository()
    repository.add("E0001", 50_000.0)
    repository.add("E0002", 30_000.0)
    assert payroll_of(repository, ["E0001", "E0002", "E0003"]) == 80_000.0
    assert repository.items == {"E0001": 50_000.0, "E0002": 30_000.0}  # state testing
