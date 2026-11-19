"""YAML configuration (departments, salary limits) + environment overrides."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from employee_app.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class AppConfig:
    departments: dict[str, str]  # code -> name
    min_salary: float
    max_salary: float
    currency: str
    skip_invalid: bool


def get_min_salary(default: float) -> float:
    """Minimum salary can be overridden by the EMPLOYEE_MIN_SALARY environment variable."""
    value = os.getenv("EMPLOYEE_MIN_SALARY")
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ConfigurationError("EMPLOYEE_MIN_SALARY must be numeric") from error


def load_config(path: Path) -> AppConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError("Invalid YAML configuration") from error
    try:
        config = AppConfig(
            departments={str(code).upper(): str(name)
                         for code, name in raw["departments"].items()},
            min_salary=get_min_salary(float(raw["min_salary"])),
            max_salary=float(raw.get("max_salary", 1_000_000)),
            currency=str(raw.get("currency", "UAH")).upper(),
            skip_invalid=bool(raw.get("skip_invalid", True)),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ConfigurationError("Configuration structure is invalid") from error
    if not config.departments:
        raise ConfigurationError("At least one department is required")
    if not 0 <= config.min_salary < config.max_salary:
        raise ConfigurationError("Expected 0 <= min_salary < max_salary")
    if len(config.currency) != 3:
        raise ConfigurationError("currency must be a 3-letter code")
    return config
