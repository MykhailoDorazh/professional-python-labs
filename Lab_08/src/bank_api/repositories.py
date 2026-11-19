"""Repository Pattern: SQL details are hidden from the service layer.

Repositories only add/flush objects; COMMIT/ROLLBACK is decided by the caller
(``database.transaction``), so several repository calls form one transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bank_api.exceptions import ClientNotFoundError, DuplicateAccountError
from bank_api.models import Account, Base, Client, Transaction

ModelT = TypeVar("ModelT", bound=Base)

UK_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"


def uk_key(text: str) -> tuple[tuple[int, int], ...]:
    """Sort key that follows the Ukrainian alphabet (А < ... < І < ... < Я)."""
    return tuple(
        (1, UK_ALPHABET.index(ch)) if ch in UK_ALPHABET else (0, ord(ch))
        for ch in text.lower()
    )


class SqlAlchemyRepository(Generic[ModelT]):
    """Generic CRUD for one ORM model."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()  # INSERT now -> primary key is assigned
        return entity

    def get_by_id(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def get_all(self, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        statement = select(self.model).order_by(self.model.id).offset(offset)  # type: ignore[attr-defined]
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.scalars(statement))

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model)) or 0


class ClientRepository(SqlAlchemyRepository[Client]):
    model = Client

    def find_by_name(self, fragment: str) -> list[Client]:
        # the pattern is sent as a bound parameter, not glued into SQL text
        statement = select(Client).where(Client.full_name.ilike(f"%{fragment}%"))
        # SQLite ORDER BY compares code points: 'І' (U+0406) < 'А' (U+0410),
        # so the Ukrainian alphabetical order is applied in Python.
        return sorted(self.session.scalars(statement), key=lambda c: uk_key(c.full_name))


class AccountRepository(SqlAlchemyRepository[Account]):
    model = Account

    def add(self, entity: Account) -> Account:
        """INSERT an account; translate DB constraint errors into domain errors.

        The caller's ``transaction()`` block performs the ROLLBACK.
        """
        try:
            return super().add(entity)
        except IntegrityError as error:
            message = str(error.orig)
            if "UNIQUE" in message:
                raise DuplicateAccountError(f"Рахунок {entity.number} вже існує") from error
            if "FOREIGN KEY" in message:
                raise ClientNotFoundError(f"Клієнта id={entity.client_id} не існує") from error
            raise

    def get_by_number(self, number: str) -> Account | None:
        return self.session.scalar(select(Account).where(Account.number == number))

    def get_for_update(self, number: str) -> Account | None:
        """SELECT ... FOR UPDATE (ignored by SQLite, row lock on PostgreSQL)."""
        return self.session.scalar(
            select(Account).where(Account.number == number).with_for_update()
        )

    def list_by_client(self, client_id: int) -> list[Account]:
        statement = (
            select(Account).where(Account.client_id == client_id).order_by(Account.number)
        )
        return list(self.session.scalars(statement))

    def filter(
        self,
        *,
        min_balance_cents: int | None = None,
        account_type: str | None = None,
        order_by_balance: bool = False,
    ) -> list[Account]:
        statement = select(Account)
        if min_balance_cents is not None:
            statement = statement.where(Account.balance_cents >= min_balance_cents)
        if account_type is not None:
            statement = statement.where(Account.account_type == account_type)
        statement = statement.order_by(
            Account.balance_cents.desc() if order_by_balance else Account.number
        )
        return list(self.session.scalars(statement))

    def total_balance_cents(self) -> int:
        return self.session.scalar(select(func.coalesce(func.sum(Account.balance_cents), 0))) or 0


class TransactionRepository(SqlAlchemyRepository[Transaction]):
    model = Transaction

    def list_for_account(self, account_id: int) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.id)
        )
        return list(self.session.scalars(statement))

    def turnover_cents(self) -> int:
        """Sum of all deposits and withdrawals (transfers are counted once)."""
        statement = select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
            Transaction.kind.in_(("deposit", "withdraw", "transfer_out"))
        )
        return self.session.scalar(statement) or 0

    def stats_by_kind(self) -> Sequence[tuple[str, int, int, float]]:
        """COUNT / SUM / AVG of amounts grouped by operation kind."""
        statement = (
            select(
                Transaction.kind,
                func.count(Transaction.id),
                func.sum(Transaction.amount_cents),
                func.avg(Transaction.amount_cents),
            )
            .group_by(Transaction.kind)
            .order_by(Transaction.kind)
        )
        return [(k, c, s, float(a)) for k, c, s, a in self.session.execute(statement)]
