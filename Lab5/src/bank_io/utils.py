"""Helpers: masking of confidential data and a logging context manager."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

logger = logging.getLogger(__name__)


def mask_account(number: str) -> str:
    """UA10000123 -> UA******23: повний номер рахунку не потрапляє в логи."""
    if len(number) <= 4:
        return "*" * len(number)
    return number[:2] + "*" * (len(number) - 4) + number[-2:]


def mask_client(name: str) -> str:
    """Іван Петренко -> І*** П***."""
    return " ".join(part[:1] + "***" for part in name.split()) or "<empty>"


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
