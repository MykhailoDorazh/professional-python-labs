from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from bank_app.config import get_currency, load_config
from bank_app.exceptions import ConfigurationError

VALID = "allowed_operations: [deposit, withdraw]\ncurrency: uah\nmax_amount: 500\n"


def test_load_valid_config(write_file: Callable[[str, str], Path]) -> None:
    config = load_config(write_file("config.yaml", VALID))
    assert config.allowed_operations == ("deposit", "withdraw")
    assert config.currency == "UAH"
    assert config.max_amount == pytest.approx(500)
    assert config.skip_invalid is True


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found") as exc_info:
        load_config(tmp_path / "absent.yaml")
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_invalid_yaml_keeps_original_cause(write_file: Callable[[str, str], Path]) -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(write_file("bad.yaml", "allowed_operations: [deposit"))
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("currency: UAH\nmax_amount: 1\n", id="no-operations"),
        pytest.param("allowed_operations: [transfer]\ncurrency: UAH\nmax_amount: 1\n",
                     id="unknown-operation"),
        pytest.param("allowed_operations: [deposit]\ncurrency: UAH\nmax_amount: 0\n",
                     id="zero-max-amount"),
        pytest.param("allowed_operations: [deposit]\ncurrency: HRYVNIA\nmax_amount: 1\n",
                     id="bad-currency"),
        pytest.param("allowed_operations: [deposit]\ncurrency: UAH\nmax_amount: lots\n",
                     id="non-numeric-max"),
    ],
)
def test_invalid_configuration(write_file: Callable[[str, str], Path], text: str) -> None:
    with pytest.raises(ConfigurationError):
        load_config(write_file("config.yaml", text))


def test_currency_from_environment(monkeypatch: pytest.MonkeyPatch,
                                   write_file: Callable[[str, str], Path]) -> None:
    monkeypatch.setenv("BANK_CURRENCY", "usd")
    assert get_currency() == "USD"
    assert load_config(write_file("config.yaml", VALID)).currency == "USD"


def test_default_currency_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BANK_CURRENCY", raising=False)
    assert get_currency() == "UAH"
    assert get_currency("eur") == "EUR"
