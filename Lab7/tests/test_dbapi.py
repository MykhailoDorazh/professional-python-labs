"""Plain sqlite3 (DB-API) access to the same database file."""

from pathlib import Path

import pytest

from bank_db.dbapi import deposit_raw, find_account_by_number, table_ddl
from bank_db.services import BankService


def test_find_account_by_number(seeded: BankService, db_path: Path) -> None:
    row = find_account_by_number(db_path, "UA2")
    assert row is not None
    assert (row.number, row.client, row.account_type, row.balance_cents, row.operations) == (
        "UA2", "Анна Коваль", "savings", 50000, 1)


def test_unknown_number_returns_none(seeded: BankService, db_path: Path) -> None:
    assert find_account_by_number(db_path, "UA404") is None


def test_sql_injection_is_not_possible(seeded: BankService, db_path: Path) -> None:
    assert find_account_by_number(db_path, "' OR '1'='1") is None


def test_raw_deposit_commit(seeded: BankService, db_path: Path) -> None:
    deposit_raw(db_path, "UA3", 7000)
    seeded.session.expire_all()
    assert seeded.get_account("UA3").balance_cents == 7000
    assert [t.kind for t in seeded.history("UA3")] == ["deposit"]


def test_raw_deposit_rollback(seeded: BankService, db_path: Path) -> None:
    with pytest.raises(LookupError):
        deposit_raw(db_path, "UA404", 100)
    assert find_account_by_number(db_path, "UA1").balance_cents == 100000  # type: ignore[union-attr]


def test_ddl_contains_keys(seeded: BankService, db_path: Path) -> None:
    clients, accounts, transactions = table_ddl(db_path)
    assert "PRIMARY KEY (id)" in clients
    assert "REFERENCES clients (id) ON DELETE CASCADE" in accounts
    assert "REFERENCES accounts (id) ON DELETE CASCADE" in transactions
