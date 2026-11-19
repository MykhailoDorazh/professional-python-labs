"""Experiment 4: Mock vs Fake for the same function."""

from unittest.mock import Mock

from exp_code import FakeRepository, total_of


def test_total_with_mock() -> None:
    repository = Mock()
    repository.get.side_effect = lambda number: {"UA1": 100.0, "UA2": 50.0}.get(number)
    assert total_of(repository, ["UA1", "UA2", "UA3"]) == 150.0
    assert repository.get.call_count == 3  # interaction testing


def test_total_with_fake() -> None:
    repository = FakeRepository()
    repository.add("UA1", 100.0)
    repository.add("UA2", 50.0)
    assert total_of(repository, ["UA1", "UA2", "UA3"]) == 150.0
    assert repository.items == {"UA1": 100.0, "UA2": 50.0}  # state testing
