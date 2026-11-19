"""Generic in-memory repository (custom collection class)."""

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from bank_domain.exceptions import DuplicateAccountError
from bank_domain.protocols import HasKey

T = TypeVar("T", bound=HasKey)  # bound TypeVar: зберігати можна лише об'єкти з .key


class InMemoryRepository(Generic[T]):
    """Repository[T]: one reusable class for accounts, customers, etc."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def add(self, item: T) -> None:
        if item.key in self._items:
            raise DuplicateAccountError(f"Запис {item.key} вже існує")
        self._items[item.key] = item

    def get(self, key: str) -> T | None:
        return self._items.get(key.upper())

    def remove(self, key: str) -> bool:
        return self._items.pop(key.upper(), None) is not None

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self._items.values() if predicate(item)]

    def all(self) -> list[T]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key.upper() in self._items

    def __getitem__(self, key: str) -> T:
        return self._items[key.upper()]
