"""YAML configuration + environment overrides."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from bank_app.exceptions import ConfigurationError

KNOWN_OPERATIONS = frozenset({"deposit", "withdraw"})


@dataclass(frozen=True, slots=True)
class AppConfig:
    allowed_operations: tuple[str, ...]
    currency: str
    max_amount: float
    skip_invalid: bool


def get_currency(default: str = "UAH") -> str:
    """Currency can be overridden by the BANK_CURRENCY environment variable."""
    return os.getenv("BANK_CURRENCY", default).upper()


def load_config(path: Path) -> AppConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError("Invalid YAML configuration") from error
    try:
        config = AppConfig(
            allowed_operations=tuple(raw["allowed_operations"]),
            currency=get_currency(str(raw["currency"])),
            max_amount=float(raw["max_amount"]),
            skip_invalid=bool(raw.get("skip_invalid", True)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError("Configuration structure is invalid") from error
    if not config.allowed_operations or not set(config.allowed_operations) <= KNOWN_OPERATIONS:
        raise ConfigurationError(f"Unknown operations: {config.allowed_operations}")
    if config.max_amount <= 0:
        raise ConfigurationError("max_amount must be positive")
    if len(config.currency) != 3:
        raise ConfigurationError("currency must be a 3-letter code")
    return config
