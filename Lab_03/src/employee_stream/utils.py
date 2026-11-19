"""Small generator utilities."""

from collections.abc import Iterator
from itertools import count, islice
from typing import Any


def employee_ids(start: int = 100_000) -> Iterator[str]:
    """Infinite generator of employee ids E100000, E100001, ...
    Must always be limited (islice), list(employee_ids()) never ends."""
    for value in count(start):
        yield f"E{value:06d}"


def take(n: int, iterable: Any) -> list:
    """First n elements of any (even infinite) iterable."""
    return list(islice(iterable, n))


def flatten(values: Any) -> Iterator[Any]:
    """Recursive generator: flattens nested lists with yield from."""
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value
