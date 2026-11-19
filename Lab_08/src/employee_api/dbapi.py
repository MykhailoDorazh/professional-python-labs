"""Plain Python DB-API (sqlite3) access without ORM — parameterized queries only."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import NamedTuple


class EmployeeRow(NamedTuple):
    personnel_number: str
    full_name: str
    position: str
    salary_cents: int


FIND_BY_DEPARTMENT_SQL = """
    SELECT e.personnel_number, e.full_name, e.position, e.salary_cents
    FROM employees AS e
    JOIN departments AS d ON d.id = e.department_id
    WHERE d.code = ?
    ORDER BY e.salary_cents DESC, e.personnel_number
"""


def find_by_department(database: str | Path, code: str) -> list[EmployeeRow]:
    """Parameterized search by department code: the value is sent separately from SQL."""
    with closing(sqlite3.connect(database)) as connection:
        cursor = connection.execute(FIND_BY_DEPARTMENT_SQL, (code,))
        return [EmployeeRow(*row) for row in cursor.fetchall()]


def raise_salary_raw(database: str | Path, code: str, percent: float) -> int:
    """Mass salary change with an explicit DB-API transaction: commit or rollback."""
    with closing(sqlite3.connect(database)) as connection:
        try:
            cursor = connection.execute(
                "UPDATE employees SET salary_cents = CAST(ROUND(salary_cents * ?) AS INTEGER) "
                "WHERE department_id = (SELECT id FROM departments WHERE code = ?)",
                (1 + percent / 100, code),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"У відділі {code} немає працівників")
            connection.commit()
            return cursor.rowcount
        except Exception:
            connection.rollback()
            raise


def table_ddl(database: str | Path) -> list[str]:
    """CREATE TABLE statements stored in sqlite_master."""
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name IN ('departments', 'employees') ORDER BY rowid"
        ).fetchall()
        return [sql for (sql,) in rows]
