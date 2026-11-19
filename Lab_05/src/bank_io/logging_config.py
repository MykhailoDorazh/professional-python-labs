"""Logging configuration: file with rotation + console."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(level: str, path: Path, *, console: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
    ]
    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(levelname)-7s | %(message)s"))
        handlers.append(stream)
    handlers[0].setFormatter(logging.Formatter(FORMAT))
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        handlers=handlers, force=True)
