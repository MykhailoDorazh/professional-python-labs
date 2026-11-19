"""ACID on SQLite: what each letter means in practice for the employee database."""

import sqlite3
import tempfile
from pathlib import Path

db = Path(tempfile.mkdtemp()) / "acid.db"
setup = sqlite3.connect(db)
setup.executescript("""
    CREATE TABLE employees (number TEXT PRIMARY KEY, department TEXT NOT NULL,
                            salary_cents INTEGER NOT NULL
                            CHECK (salary_cents BETWEEN 0 AND 100000000));
    INSERT INTO employees VALUES ('E0001', 'IT', 9000000), ('E0002', 'IT', 6000000);
""")
setup.commit()
setup.close()


def state(conn: sqlite3.Connection) -> dict[str, tuple[str, int]]:
    rows = conn.execute("SELECT number, department, salary_cents FROM employees ORDER BY number")
    return {number: (dept, cents // 100) for number, dept, cents in rows}


a = sqlite3.connect(db, isolation_level="DEFERRED", timeout=0.1)
b = sqlite3.connect(db, isolation_level="DEFERRED", timeout=0.1)

print("A — Atomicity: масове переведення IT -> FIN, збій після першого UPDATE")
try:
    a.execute("UPDATE employees SET department = 'FIN' WHERE number = 'E0001'")
    raise ConnectionError("збій між двома UPDATE")
except ConnectionError as error:
    a.rollback()
    print(f"   {error} -> ROLLBACK: {state(a)}")

print("C — Consistency: CHECK (salary_cents BETWEEN 0 AND 100000000)")
try:
    a.execute("UPDATE employees SET salary_cents = salary_cents * 12")  # E0001 -> 1 080 000
except sqlite3.IntegrityError as error:
    a.rollback()
    print(f"   IntegrityError: {error}; зарплати не змінились: {state(a)}")

print("I — Isolation: A підвищує зарплати на 10 %, але ще не зробив COMMIT")
a.execute("UPDATE employees SET salary_cents = salary_cents * 11 / 10")
print(f"   A бачить свої зміни : {state(a)}")
print(f"   B бачить            : {state(b)}  <- незафіксовані зміни невидимі")
a.commit()
print(f"   після COMMIT B бачить: {state(b)}")

print("D — Durability: нове з'єднання після закриття старих")
a.close()
b.close()
c = sqlite3.connect(db)
print(f"   {state(c)}")
c.close()
