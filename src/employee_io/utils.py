"""Helpers: masking of confidential data and a logging context manager."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

logger = logging.getLogger(__name__)


def mask_id(employee_id: str) -> str:
    """E100123 -> E1****3: повний табельний номер не потрапляє в логи."""
    if len(employee_id) <= 3:
        return "*" * len(employee_id)
    return employee_id[:2] + "*" * (len(employee_id) - 3) + employee_id[-1:]


def mask_name(name: str) -> str:
    """Іван Петренко -> І*** П***."""
    return " ".join(part[:1] + "***" for part in name.split()) or "<empty>"


def salary_band(salary: float, step: int = 10_000) -> str:
    """Instead of the exact salary only a band is logged: 52000 -> '50000-59999'."""
    low = int(salary // step * step)
    return f"{low}-{low + step - 1}"


@contextmanager
def logged_operation(operation: str) -> Iterator[None]:
    """Logs start, duration and failure of a block of code."""
    logger.info("%s started", operation)
    start = perf_counter()
    try:
        yield
    except Exception:
        logger.exception("%s failed after %.3f s", operation, perf_counter() - start)
        raise
    else:
        logger.info("%s finished in %.3f s", operation, perf_counter() - start)
