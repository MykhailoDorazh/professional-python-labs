"""Plain Python DB-API (sqlite3) access without ORM — parameterized queries only."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple


class AccountRow(NamedTuple):
    number: str
    client: str
    account_type: str
    balance_cents: int
    operations: int


FIND_BY_NUMBER_SQL = """
    SELECT a.number, c.full_name, a.account_type, a.balance_cents,
           COUNT(t.id) AS operations
    FROM accounts AS a
    JOIN clients AS c ON c.id = a.client_id
    LEFT JOIN transactions AS t ON t.account_id = a.id
    WHERE a.number = ?
    GROUP BY a.id
"""


def find_account_by_number(database: str | Path, number: str) -> AccountRow | None:
    """Parameterized search by account number: the value is sent separately from SQL."""
    connection = sqlite3.connect(database)
    try:
        cursor = connection.cursor()
        cursor.execute(FIND_BY_NUMBER_SQL, (number,))
        row = cursor.fetchone()
        return AccountRow(*row) if row else None
    finally:
        connection.close()


def deposit_raw(database: str | Path, number: str, cents: int) -> None:
    """Deposit with explicit DB-API transaction: UPDATE + INSERT, commit or rollback."""
    connection = sqlite3.connect(database)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE number = ?",
            (cents, number),
        )
        if cursor.rowcount != 1:
            raise LookupError(f"Рахунок {number} не знайдено")
        cursor.execute(
            "INSERT INTO transactions (account_id, kind, amount_cents, "
            "balance_after_cents, created_at) "
            "SELECT id, 'deposit', ?, balance_cents, datetime('now') "
            "FROM accounts WHERE number = ?",
            (cents, number),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def table_ddl(database: str | Path) -> list[str]:
    """CREATE TABLE statements stored in sqlite_master."""
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name IN ('clients', 'accounts', 'transactions') ORDER BY rowid"
        ).fetchall()
        return [sql for (sql,) in rows]
    finally:
        connection.close()
