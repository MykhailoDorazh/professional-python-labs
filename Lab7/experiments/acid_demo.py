"""ACID on SQLite: what each letter means in practice for the bank database."""

import sqlite3
import tempfile
from pathlib import Path

db = Path(tempfile.mkdtemp()) / "acid.db"
setup = sqlite3.connect(db)
setup.executescript("""
    CREATE TABLE accounts (number TEXT PRIMARY KEY,
                           balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0));
    INSERT INTO accounts VALUES ('UA1', 100000), ('UA2', 0);
""")
setup.commit()
setup.close()


def balances(conn: sqlite3.Connection) -> dict[str, int]:
    return dict(conn.execute("SELECT number, balance_cents FROM accounts ORDER BY number"))


a = sqlite3.connect(db, isolation_level="DEFERRED", timeout=0.1)
b = sqlite3.connect(db, isolation_level="DEFERRED", timeout=0.1)

print("A — Atomicity: переказ 300.00, збій після списання")
try:
    a.execute("UPDATE accounts SET balance_cents = balance_cents - 30000 WHERE number='UA1'")
    raise ConnectionError("збій між двома UPDATE")
except ConnectionError as error:
    a.rollback()
    print(f"   {error} -> ROLLBACK, баланси: {balances(a)}")

print("C — Consistency: CHECK (balance_cents >= 0)")
try:
    a.execute("UPDATE accounts SET balance_cents = balance_cents - 999999 WHERE number='UA1'")
except sqlite3.IntegrityError as error:
    a.rollback()
    print(f"   IntegrityError: {error}")

print("I — Isolation: A змінює дані, але ще не зробив COMMIT")
a.execute("UPDATE accounts SET balance_cents = balance_cents - 20000 WHERE number='UA1'")
a.execute("UPDATE accounts SET balance_cents = balance_cents + 20000 WHERE number='UA2'")
print(f"   A бачить свої зміни : {balances(a)}")
print(f"   B бачить            : {balances(b)}  <- незафіксовані зміни невидимі")
a.commit()
print(f"   після COMMIT B бачить: {balances(b)}")

print("D — Durability: нове з'єднання після закриття старих")
a.close()
b.close()
c = sqlite3.connect(db)
print(f"   {balances(c)}")
c.close()
