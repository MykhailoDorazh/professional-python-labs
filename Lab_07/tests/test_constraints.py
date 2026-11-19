"""Database-level guarantees: CHECK, UNIQUE, FOREIGN KEY (enforced by SQLite PRAGMA)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bank_db.database import transaction
from bank_db.models import Account, Client, Transaction
from bank_db.services import BankService


def test_check_constraint_forbids_negative_balance(seeded: BankService) -> None:
    """Even code that bypasses the service cannot store a negative balance."""
    with pytest.raises(IntegrityError, match="ck_accounts_balance_non_negative"):
        with transaction(seeded.session):
            seeded.session.execute(
                text("UPDATE accounts SET balance_cents = -1 WHERE number = :n"), {"n": "UA1"}
            )
    seeded.session.expire_all()
    assert seeded.get_account("UA1").balance_cents == 100000


def test_check_constraint_on_transaction_amount(seeded: BankService) -> None:
    account = seeded.get_account("UA1")
    with pytest.raises(IntegrityError):
        with transaction(seeded.session):
            seeded.transactions.add(Transaction(account_id=account.id, kind="deposit",
                                                amount_cents=0, balance_after_cents=0))


def test_check_constraint_on_account_type(session: Session) -> None:
    with pytest.raises(IntegrityError):
        with transaction(session):
            client = Client(full_name="Анна")
            session.add(client)
            session.flush()
            session.add(Account(number="UA1", client_id=client.id, account_type="crypto"))


def test_unique_account_number(session: Session) -> None:
    with pytest.raises(IntegrityError):
        with transaction(session):
            client = Client(full_name="Анна")
            session.add(client)
            session.flush()
            session.add_all([Account(number="UA1", client_id=client.id),
                             Account(number="UA1", client_id=client.id)])


def test_foreign_key_is_enforced(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        with transaction(session):
            session.execute(text(
                "INSERT INTO accounts (number, balance_cents, client_id, account_type) "
                "VALUES ('UA9', 0, 999, 'current')"))
