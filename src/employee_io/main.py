"""Entry point: python -m employee_io.main [--config config.yaml] [--strict] [--min-salary N]."""

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from employee_io.app import run_pipeline
from employee_io.config import load_config
from employee_io.exceptions import ApplicationError, ConfigurationError
from employee_io.logging_config import configure_logging

logger = logging.getLogger("employee_io")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Employee data import/export")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--strict", action="store_true", help="override skip_invalid=false")
    parser.add_argument("--min-salary", type=float, help="override processing.min_salary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        processing = config.processing
        if args.strict:
            processing = replace(processing, skip_invalid=False)
        if args.min_salary is not None:
            if not 0 <= args.min_salary < processing.max_salary:
                raise ConfigurationError("--min-salary must be in [0, max_salary)")
            processing = replace(processing, min_salary=args.min_salary)
        config = replace(config, processing=processing)
        configure_logging(config.logging.level, config.logging.path)
        statistics = run_pipeline(config)
    except ApplicationError as error:
        if not logging.getLogger().handlers:  # конфігурація ще не завантажена
            logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")
        logger.error("Application error: %s: %s", type(error).__name__, error)
        raise SystemExit(1) from error
    def money(value: float) -> str:
        return f"{value:,.2f}".replace(",", " ")

    currency = config.processing.currency
    print(f"Результат: {config.output_path.as_posix()} ({statistics.exported} працівників, "
          f"фонд {money(statistics.payroll)} {currency}, середня "
          f"{money(statistics.average_salary)} {currency})")
    print(f"Помилки: {config.errors_path.as_posix()}, звіт: {config.summary_path.as_posix()}")


if __name__ == "__main__":
    main()
