"""Why SQL must not be built with f-strings: the same search, unsafe vs parameterized."""

import sqlite3

connection = sqlite3.connect(":memory:")
connection.executescript("""
    CREATE TABLE employees (personnel_number TEXT PRIMARY KEY, full_name TEXT,
                            department TEXT, salary_cents INTEGER);
    INSERT INTO employees VALUES ('E0001', 'Олена Коваль', 'IT', 9500000),
                                 ('E0002', 'Андрій Мельник', 'FIN', 3680050),
                                 ('E0003', 'Марія Бондар', 'HR', 4800000);
""")


def find_unsafe(department: str) -> list[tuple[str, str, str, int]]:
    query = f"SELECT * FROM employees WHERE department = '{department}'"  # DANGEROUS
    print("   SQL:", query)
    return connection.execute(query).fetchall()


def find_safe(department: str) -> list[tuple[str, str, str, int]]:
    return connection.execute("SELECT * FROM employees WHERE department = ?",
                              (department,)).fetchall()


attack = "x' OR '1'='1"
print("1) f-string, звичайне значення FIN:")
print("  ", find_unsafe("FIN"))
print(f"2) f-string, значення {attack!r}:")
print("  ", find_unsafe(attack), "<- витік зарплат УСІХ відділів")
print(f"3) parameterized query, значення {attack!r}:")
print("  ", find_safe(attack), "<- значення трактується як звичайний рядок")
