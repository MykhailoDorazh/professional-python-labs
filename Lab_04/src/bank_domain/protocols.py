"""Structural interfaces (Protocols)."""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from bank_domain.models import Account


class Notifier(Protocol):
    """Anything that can deliver a message to a recipient."""

    def send(self, recipient: str, message: str) -> None: ...


@runtime_checkable
class HasKey(Protocol):
    """Object that can be stored in the generic repository."""

    @property
    def key(self) -> str: ...


# Interface segregation: звітам потрібне лише читання, сервісу - читання і запис.
class AccountReader(Protocol):
    def get(self, key: str) -> Account | None: ...

    def __iter__(self) -> Iterator[Account]: ...


class AccountStore(AccountReader, Protocol):
    def add(self, item: Account) -> None: ...
