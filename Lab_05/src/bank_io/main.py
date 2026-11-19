"""Entry point: python -m bank_io.main [--config config.yaml] [--strict]."""

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from bank_io.app import run_pipeline
from bank_io.config import load_config
from bank_io.exceptions import ApplicationError
from bank_io.logging_config import configure_logging

logger = logging.getLogger("bank_io")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bank operations import/export")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--strict", action="store_true", help="override skip_invalid=false")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        if args.strict:
            config = replace(config, processing=replace(config.processing, skip_invalid=False))
        configure_logging(config.logging.level, config.logging.path)
        statistics = run_pipeline(config)
    except ApplicationError as error:
        if not logging.getLogger().handlers:  # конфігурація ще не завантажена
            logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")
        logger.error("Application error: %s: %s", type(error).__name__, error)
        raise SystemExit(1) from error
    print(f"Результат: {config.output_path.as_posix()} ({statistics.exported} записів), "
          f"помилки: {config.errors_path.as_posix()}, звіт: {config.summary_path.as_posix()}")


if __name__ == "__main__":
    main()
