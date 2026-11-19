"""Structural interfaces (Protocols)."""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from employee_domain.models import Employee


class Notifier(Protocol):
    """Anything that can deliver a message to a recipient."""

    def send(self, recipient: str, message: str) -> None: ...


@runtime_checkable
class HasKey(Protocol):
    """Object that can be stored in the generic repository."""

    @property
    def key(self) -> str: ...


# Interface segregation: звітам потрібне лише читання, HR-сервісу - читання і запис.
class EmployeeReader(Protocol):
    def get(self, key: str) -> Employee | None: ...

    def __iter__(self) -> Iterator[Employee]: ...


class EmployeeStore(EmployeeReader, Protocol):
    def add(self, item: Employee) -> None: ...
