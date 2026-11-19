"""Service layer: business rules of the bank; persistence is delegated to repositories."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bank_perf.database import transaction
from bank_perf.exceptions import (
    AccountNotEmptyError,
    AccountNotFoundError,
    BankError,
    ClientNotFoundError,
    InsufficientFundsError,
)
from bank_perf.models import Account, Client, Transaction
from bank_perf.money import from_cents, to_cents
from bank_perf.repositories import AccountRepository, ClientRepository, TransactionRepository

ACCOUNT_TYPES = ("current", "savings")


class BankService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.clients = ClientRepository(session)
        self.accounts = AccountRepository(session)
        self.transactions = TransactionRepository(session)

    # ---------- clients ----------
    def register_client(self, full_name: str, email: str | None = None) -> Client:
        if not full_name.strip():
            raise BankError("Ім'я клієнта не може бути порожнім")
        with transaction(self.session):
            return self.clients.add(Client(full_name=full_name.strip(), email=email))

    def get_client(self, client_id: int) -> Client:
        client = self.clients.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"Клієнта id={client_id} не знайдено")
        return client

    def rename_client(self, client_id: int, full_name: str) -> Client:
        with transaction(self.session):
            client = self.get_client(client_id)
            client.full_name = full_name
            return client

    def delete_client(self, client_id: int) -> None:
        """Delete a client together with accounts and history (ON DELETE CASCADE)."""
        with transaction(self.session):
            self.clients.delete(self.get_client(client_id))

    # ---------- accounts ----------
    def open_account(
        self,
        client_id: int,
        number: str,
        initial: Decimal | str | int = 0,
        account_type: str = "current",
    ) -> Account:
        if account_type not in ACCOUNT_TYPES:
            raise BankError(f"Невідомий тип рахунку: {account_type}")
        with transaction(self.session):
            account = self.accounts.add(
                Account(number=number, client_id=client_id, account_type=account_type)
            )
            if Decimal(str(initial)) != 0:
                self._credit(account, to_cents(initial), "deposit")
            return account

    def get_account(self, number: str) -> Account:
        account = self.accounts.get_by_number(number)
        if account is None:
            raise AccountNotFoundError(f"Рахунок {number} не знайдено")
        return account

    def get_account_by_id(self, account_id: int) -> Account:
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(f"Рахунок id={account_id} не знайдено")
        return account

    def get_balance(self, number: str) -> Decimal:
        return from_cents(self.get_account(number).balance_cents)

    def change_account_type(self, number: str, account_type: str) -> Account:
        if account_type not in ACCOUNT_TYPES:
            raise BankError(f"Невідомий тип рахунку: {account_type}")
        with transaction(self.session):
            account = self.get_account(number)
            account.account_type = account_type
            return account

    def close_account(self, number: str) -> None:
        with transaction(self.session):
            account = self.get_account(number)
            if account.balance_cents != 0:
                raise AccountNotEmptyError(f"На рахунку {number} ще є кошти")
            self.accounts.delete(account)

    # ---------- money operations ----------
    def deposit(self, number: str, amount: Decimal | str | int) -> Transaction:
        cents = to_cents(amount)
        with transaction(self.session):
            return self._credit(self.get_account(number), cents, "deposit")

    def withdraw(self, number: str, amount: Decimal | str | int) -> Transaction:
        cents = to_cents(amount)
        with transaction(self.session):
            return self._debit(self.get_account(number), cents, "withdraw")

    def transfer_money(
        self, source: str, target: str, amount: Decimal | str | int
    ) -> tuple[Transaction, Transaction]:
        """Atomic transfer: debit + credit + two history records, or nothing at all."""
        cents = to_cents(amount)
        if source == target:
            raise BankError("Неможливо переказати кошти на той самий рахунок")
        with transaction(self.session):
            # lock rows in a stable order to avoid deadlocks on real DBMS
            first, second = sorted((source, target))
            locked = {n: self.accounts.get_for_update(n) for n in (first, second)}
            src, dst = locked[source], locked[target]
            if src is None:
                raise AccountNotFoundError(f"Рахунок {source} не знайдено")
            out = self._debit(src, cents, "transfer_out", counterparty=target)
            if dst is None:  # the debit above is undone by ROLLBACK
                raise AccountNotFoundError(f"Рахунок {target} не знайдено")
            inc = self._credit(dst, cents, "transfer_in", counterparty=source)
            return out, inc

    def history(self, number: str) -> list[Transaction]:
        return self.transactions.list_for_account(self.get_account(number).id)

    # ---------- reports ----------
    def total_funds(self) -> Decimal:
        return from_cents(self.accounts.total_balance_cents())

    def turnover(self) -> Decimal:
        return from_cents(self.transactions.turnover_cents())

    def client_summary(self) -> list[tuple[str, int, Decimal]]:
        """JOIN clients-accounts + GROUP BY: accounts count and money per client."""
        statement = (
            select(
                Client.full_name,
                func.count(Account.id),
                func.coalesce(func.sum(Account.balance_cents), 0),
            )
            .join(Account, Account.client_id == Client.id, isouter=True)
            .group_by(Client.id)
            .order_by(func.sum(Account.balance_cents).desc())
        )
        return [(n, c, from_cents(s)) for n, c, s in self.session.execute(statement)]

    # ---------- internal ----------
    def _credit(
        self, account: Account, cents: int, kind: str, counterparty: str | None = None
    ) -> Transaction:
        account.balance_cents += cents
        return self.transactions.add(
            Transaction(
                account_id=account.id,
                kind=kind,
                amount_cents=cents,
                balance_after_cents=account.balance_cents,
                counterparty=counterparty,
            )
        )

    def _debit(
        self, account: Account, cents: int, kind: str, counterparty: str | None = None
    ) -> Transaction:
        if account.balance_cents < cents:
            raise InsufficientFundsError(
                f"Недостатньо коштів на {account.number}: "
                f"{from_cents(account.balance_cents)} < {from_cents(cents)}"
            )
        account.balance_cents -= cents
        return self.transactions.add(
            Transaction(
                account_id=account.id,
                kind=kind,
                amount_cents=cents,
                balance_after_cents=account.balance_cents,
                counterparty=counterparty,
            )
        )
