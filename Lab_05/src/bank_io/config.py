"""Loading and validation of the YAML configuration (fail-fast)."""

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from bank_io.exceptions import ConfigurationError
from bank_io.models import AppConfig, LoggingConfig, ProcessingConfig

SUPPORTED_SCHEMA = 1
KNOWN_OPERATIONS = frozenset({"deposit", "withdraw"})
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
    """BANK_IO_INPUT and BANK_IO_SKIP_INVALID override values from the file."""
    if "BANK_IO_INPUT" in env:
        raw.setdefault("input", {})["path"] = env["BANK_IO_INPUT"]
    if "BANK_IO_SKIP_INVALID" in env:
        raw.setdefault("processing", {})["skip_invalid"] = (
            env["BANK_IO_SKIP_INVALID"].strip().lower() in {"1", "true", "yes"})
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
                allowed_operations=tuple(processing["allowed_operations"]),
                currency=str(processing["currency"]),
                max_amount=float(processing["max_amount"]),
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
    operations = set(config.processing.allowed_operations)
    if not operations or not operations <= KNOWN_OPERATIONS:
        raise ConfigurationError(
            f"allowed_operations must be a non-empty subset of {sorted(KNOWN_OPERATIONS)}")
    if config.processing.max_amount <= 0:
        raise ConfigurationError("max_amount must be positive")
    if len(config.processing.currency) != 3:
        raise ConfigurationError("currency must be a 3-letter code")
    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"Unknown logging level: {config.logging.level}")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Input file not found: {config.input_path}")
    for path in (config.output_path, config.errors_path, config.summary_path):
        if not path.parent.exists():
            # відсутній каталог для output не є помилкою - створюємо його
            path.parent.mkdir(parents=True, exist_ok=True)
