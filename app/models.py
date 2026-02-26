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
    checked INTEGER NOT NULL DEFAULT 0,
    item_id INTEGER,
    order_id INTEGER,
    qty_value REAL,
    unit TEXT,
    listed_at TEXT,
    purchased_at TEXT
);

CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS todo_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_key TEXT NOT NULL UNIQUE,
    area_label TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS todo_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT NOT NULL,
    district TEXT NOT NULL,
    item_name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE (area, district, item_name)
);

CREATE TABLE IF NOT EXISTS todo_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_date TEXT NOT NULL,
    area TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (check_date, area),
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS todo_check_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id INTEGER NOT NULL,
    district TEXT NOT NULL,
    item_name TEXT NOT NULL,
    is_missing INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    UNIQUE (check_id, district, item_name),
    FOREIGN KEY (check_id) REFERENCES todo_checks (id)
);

CREATE TABLE IF NOT EXISTS todo_order_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    qty REAL NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (check_id, item_id),
    FOREIGN KEY (check_id) REFERENCES todo_checks (id),
    FOREIGN KEY (item_id) REFERENCES items (id),
    FOREIGN KEY (order_id) REFERENCES orders (id)
);
"""


def get_db(app):
    return sqlite3.connect(app.config["DATABASE"])


def init_db(app):
    with get_db(app) as conn:
        conn.executescript(SCHEMA)
        migrate_db(conn)
        ensure_admin(conn)
        ensure_todo_areas(conn)
        ensure_todo_catalog(conn)


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

    market_columns = conn.execute("PRAGMA table_info(market_list)").fetchall()
    market_col_names = {col[1] for col in market_columns}
    if "item_id" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN item_id INTEGER")
    if "order_id" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN order_id INTEGER")
    if "qty_value" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN qty_value REAL")
    if "unit" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN unit TEXT")
    if "listed_at" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN listed_at TEXT")
    if "purchased_at" not in market_col_names:
        conn.execute("ALTER TABLE market_list ADD COLUMN purchased_at TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todo_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_key TEXT NOT NULL UNIQUE,
            area_label TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )


def ensure_todo_areas(conn):
    defaults = [
        ("bar", "Bar"),
        ("cozinha", "Cozinha"),
    ]
    for area_key, area_label in defaults:
        conn.execute(
            """
            INSERT OR IGNORE INTO todo_areas (area_key, area_label, active)
            VALUES (?, ?, 1)
            """,
            (area_key, area_label),
        )


def ensure_todo_catalog(conn):
    defaults = [
        ("bar", "Balcao", "Gelo", 1),
        ("bar", "Balcao", "Limao", 2),
        ("bar", "Balcao", "Hortela", 3),
        ("bar", "Balcao", "Guardanapos", 4),
        ("bar", "Balcao", "Palhinhas", 5),
        ("bar", "Bebidas", "Agua", 1),
        ("bar", "Bebidas", "Refrigerantes", 2),
        ("bar", "Bebidas", "Tonica", 3),
        ("bar", "Bebidas", "Cerveja Pressao", 4),
        ("bar", "Bebidas", "Vinho da Casa", 5),
        ("cozinha", "Frescos", "Cebola", 1),
        ("cozinha", "Frescos", "Alho", 2),
        ("cozinha", "Frescos", "Tomate", 3),
        ("cozinha", "Frescos", "Limao", 4),
        ("cozinha", "Frios", "Ovos", 1),
        ("cozinha", "Frios", "Manteiga", 2),
        ("cozinha", "Frios", "Natas", 3),
        ("cozinha", "Secos", "Arroz", 1),
        ("cozinha", "Secos", "Massa", 2),
        ("cozinha", "Secos", "Azeite", 3),
        ("cozinha", "Secos", "Sal", 4),
    ]
    for area, district, item_name, sort_order in defaults:
        conn.execute(
            """
            INSERT OR IGNORE INTO todo_catalog (area, district, item_name, sort_order, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (area, district, item_name, sort_order),
        )
