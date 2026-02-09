import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_subtype TEXT NOT NULL,
    unit TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    item_id INTEGER,
    qty REAL NOT NULL,
    status TEXT NOT NULL,
    total REAL NOT NULL,
    ordered_at TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (item_id) REFERENCES items (id)
);

CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    qty REAL NOT NULL,
    low_threshold REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS market_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    qty TEXT,
    notes TEXT,
    checked INTEGER NOT NULL DEFAULT 0
);
"""


def get_db(app):
    return sqlite3.connect(app.config["DATABASE"])


def init_db(app):
    with get_db(app) as conn:
        conn.executescript(SCHEMA)
        migrate_db(conn)
        ensure_admin(conn)


def ensure_admin(conn):
    cur = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if cur.fetchone():
        return
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", generate_password_hash("admin"), "admin"),
    )


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d")


def migrate_db(conn):
    columns = conn.execute("PRAGMA table_info(orders)").fetchall()
    col_names = {col[1] for col in columns}
    if "qty" not in col_names:
        conn.execute("ALTER TABLE orders ADD COLUMN qty REAL NOT NULL DEFAULT 0")
    if "item_id" not in col_names:
        conn.execute("ALTER TABLE orders ADD COLUMN item_id INTEGER")
