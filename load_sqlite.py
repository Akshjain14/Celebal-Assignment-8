import sqlite3, csv
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "ecommerce.db"
CLEAN = BASE / "data" / "cleaned"
SCHEMA = BASE / "sql" / "schema.sql"

def load_csv(conn, table, filename):
    path = CLEAN / filename
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    values = [[r[c] for c in cols] for r in rows]
    conn.executemany(sql, values)

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript(SCHEMA.read_text(encoding="utf-8"))
load_csv(conn, "customers", "customers_cleaned.csv")
load_csv(conn, "products", "products_cleaned.csv")
load_csv(conn, "orders", "orders_cleaned.csv")
load_csv(conn, "order_items", "order_items_cleaned.csv")
conn.commit()
conn.close()
print(f"Database created: {DB}")
