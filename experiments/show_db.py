"""Print the content of the SQLite database tables (DB-API, read-only)."""

import sqlite3
import sys

database = sys.argv[1] if len(sys.argv) > 1 else "demo.db"
connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
for table in ("clients", "accounts", "transactions"):
    cursor = connection.execute(f"SELECT * FROM {table}")  # table names are constants
    names = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    widths = [max(len(str(v)) for v in [n, *(r[i] for r in rows)]) for i, n in enumerate(names)]
    print(f"{table} ({len(rows)} rows)")
    print("  " + " | ".join(n.ljust(w) for n, w in zip(names, widths)))
    print("  " + "-+-".join("-" * w for w in widths))
    for row in rows:
        print("  " + " | ".join(str(v).ljust(w) for v, w in zip(row, widths)))
    print()
connection.close()
