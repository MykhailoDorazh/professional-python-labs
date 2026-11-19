"""Small generator utilities."""

from collections.abc import Iterator
from itertools import count, islice
from typing import Any


def account_numbers(start: int = 10_000_000) -> Iterator[str]:
    """Infinite generator of account numbers UA10000000, UA10000001, ...
    Must always be limited (islice), list(account_numbers()) never ends."""
    for value in count(start):
        yield f"UA{value:08d}"


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
