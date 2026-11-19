"""Why SQL must not be built with f-strings: the same search, unsafe vs parameterized."""

import sqlite3

connection = sqlite3.connect(":memory:")
connection.executescript("""
    CREATE TABLE accounts (number TEXT PRIMARY KEY, owner TEXT, balance_cents INTEGER);
    INSERT INTO accounts VALUES ('UA1', 'Анна', 100000), ('UA2', 'Олег', 50000),
                                ('UA3', 'Ірина', 777700);
""")


def find_unsafe(number: str) -> list[tuple[str, str, int]]:
    query = f"SELECT * FROM accounts WHERE number = '{number}'"  # DANGEROUS
    print("   SQL:", query)
    return connection.execute(query).fetchall()


def find_safe(number: str) -> list[tuple[str, str, int]]:
    return connection.execute("SELECT * FROM accounts WHERE number = ?", (number,)).fetchall()


attack = "x' OR '1'='1"
print("1) f-string, звичайне значення UA2:")
print("  ", find_unsafe("UA2"))
print(f"2) f-string, значення {attack!r}:")
print("  ", find_unsafe(attack), "<- витік УСІХ рахунків")
print(f"3) parameterized query, значення {attack!r}:")
print("  ", find_safe(attack), "<- значення трактується як звичайний рядок")
