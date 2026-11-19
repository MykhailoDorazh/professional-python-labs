"""Loading and validation of the YAML configuration (fail-fast)."""

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from employee_io.exceptions import ConfigurationError
from employee_io.models import AppConfig, LoggingConfig, ProcessingConfig

SUPPORTED_SCHEMA = 1
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

logger = logging.getLogger(__name__)


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)  # safe_load: без виконання довільних YAML-тегів
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML configuration: {path}") from error
    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping")
    return raw


def apply_env_overrides(raw: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    """EMPLOYEE_IO_INPUT, EMPLOYEE_IO_SKIP_INVALID and EMPLOYEE_IO_MIN_SALARY
    override values from the file."""
    if "EMPLOYEE_IO_INPUT" in env:
        raw.setdefault("input", {})["path"] = env["EMPLOYEE_IO_INPUT"]
    if "EMPLOYEE_IO_SKIP_INVALID" in env:
        raw.setdefault("processing", {})["skip_invalid"] = (
            env["EMPLOYEE_IO_SKIP_INVALID"].strip().lower() in {"1", "true", "yes"})
    if "EMPLOYEE_IO_MIN_SALARY" in env:
        raw.setdefault("processing", {})["min_salary"] = env["EMPLOYEE_IO_MIN_SALARY"]
    return raw


def load_config(path: Path, env: Mapping[str, str] | None = None) -> AppConfig:
    raw = apply_env_overrides(read_yaml(path), os.environ if env is None else env)
    base = path.parent
    try:
        if raw.get("schema_version") != SUPPORTED_SCHEMA:
            raise ConfigurationError(
                f"Unsupported schema_version: {raw.get('schema_version')!r}")
        processing = raw["processing"]
        output = raw["output"]
        config = AppConfig(
            input_path=base / raw["input"]["path"],
            output_path=base / output["path"],
            errors_path=base / output["errors_path"],
            summary_path=base / output["summary_path"],
            processing=ProcessingConfig(
                skip_invalid=bool(processing["skip_invalid"]),
                allowed_departments=tuple(str(d).strip()
                                          for d in processing["allowed_departments"]),
                min_salary=float(processing["min_salary"]),
                max_salary=float(processing["max_salary"]),
                currency=str(processing["currency"]),
            ),
            logging=LoggingConfig(
                level=str(raw["logging"]["level"]).upper(),
                path=base / raw["logging"]["path"],
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError(f"Configuration structure is invalid: {error!r}") from error
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    processing = config.processing
    departments = processing.allowed_departments
    if not departments or not all(departments):
        raise ConfigurationError("allowed_departments must be a non-empty list of names")
    if len({d.casefold() for d in departments}) != len(departments):
        raise ConfigurationError("allowed_departments contains duplicates")
    if processing.min_salary < 0:
        raise ConfigurationError("min_salary must be >= 0")
    if processing.max_salary <= processing.min_salary:
        raise ConfigurationError("max_salary must be greater than min_salary")
    if len(processing.currency) != 3:
        raise ConfigurationError("currency must be a 3-letter code")
    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"Unknown logging level: {config.logging.level}")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Input file not found: {config.input_path}")
    for path in (config.output_path, config.errors_path, config.summary_path):
        if not path.parent.exists():
            # відсутній каталог для output не є помилкою - створюємо його
            path.parent.mkdir(parents=True, exist_ok=True)
