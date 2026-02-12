import argparse
import os
import sqlite3
import sys
from datetime import datetime


DB_PATH = "data.db"


SUPPLIERS = [
    ("Delta Cafe", "Ricardo", "+351 961 578 259", "", "Cafe, cha e afins."),
    ("Superbock", "Sergio", "+351 961 130 605", "", ""),
    ("Garrafeira Rui Vinhos", "Andre", "+351 915 321 808", "", "Vinhos."),
    ("Papel Pak", "Paulo", "+351", "", "Consumiveis e embalagens."),
    ("Fernando Fernandes", "", "", "", "Descartaveis e limpeza."),
    ("Pro Gel Cone", "", "+351 912 851 503", "", "Detergentes."),
    ("Bio F.F", "", "", "", "Higiene e desinfeccao."),
]


ITEMS = [
    ("Delta Cafe", "Cafe", "Mercearia", "Despensa", "kg"),
    ("Delta Cafe", "Cha", "Mercearia", "Despensa", "cx"),
    ("Delta Cafe", "Acucar", "Mercearia", "Despensa", "kg"),
    ("Delta Cafe", "Adocante", "Mercearia", "Despensa", "cx"),
    ("Delta Cafe", "Chavenas", "Descartaveis", "Armazem", "cx"),
    ("Delta Cafe", "Guarda-sois", "Descartaveis", "Armazem", "un"),
    ("Superbock", "Cerveja Superbock", "Bebidas", "Frigorifico de bebidas", "cx"),
    ("Garrafeira Rui Vinhos", "Casal Garcia", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Aveleda", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Mateus", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Esteva tinto", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Cabriz tinto", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Melange a Trois tinto", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "BSE branco", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Monte Fuscaz (tinto e branco)", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Villa Alvor (tinto e branco)", "Vinhos", "Adega", "cx"),
    ("Papel Pak", "Sacos de vacuo", "Descartaveis", "Armazem", "cx"),
    ("Papel Pak", "Luvas cozinha", "Descartaveis", "Armazem", "cx"),
    ("Papel Pak", "Rolos termicos", "Mercearia", "Despensa", "cx"),
    ("Fernando Fernandes", "Toalhas de mesa", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Papeis zigzag", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Rolo de cozinha", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Caixa take away", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Toalitas de limao", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Lava tudo chao", "Limpeza", "Armazem", "un"),
    ("Fernando Fernandes", "Toca de cozinha", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Cheirinho do mictorio", "Limpeza", "Armazem", "un"),
    ("Fernando Fernandes", "Palhinhas", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Talher takeaway", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Copinhos takeaway", "Descartaveis", "Armazem", "cx"),
    ("Pro Gel Cone", "Sabao para maquina", "Limpeza", "Armazem", "un"),
    ("Pro Gel Cone", "Detergente", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Desengordurante", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Desinfetante", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "G19", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Alcool gel", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Blutoxol", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Sabonete liquido", "Limpeza", "Armazem", "un"),
]


STOCK = [
    ("Rolo de cozinha", "un", 8, 4),
    ("Papel higienico", "cx", 2, 3),
    ("Alcool gel", "un", 3, 2),
    ("Detergente", "un", 4, 2),
    ("Toalitas de limao", "cx", 1, 2),
]


MARKET = [
    ("Sacos de lixo 20L", "2 cx", ""),
    ("Sacos de lixo 50L", "1 cx", ""),
    ("Sabonete liquido rosa", "1 un", ""),
    ("Papel higienico", "3 cx", ""),
    ("Papel zigzag", "2 cx", ""),
    ("Rolos multibanco", "2 cx", ""),
]


ORDERS = [
    ("Delta Cafe", "Cafe", 8, "ordered", 120.0),
    ("Garrafeira Rui Vinhos", "Esteva tinto", 12, "pending", 210.0),
    ("Papel Pak", "Rolos termicos", 6, "ordered", 36.0),
    ("Fernando Fernandes", "Caixa take away", 10, "pending", 85.0),
]


def seed_db(reset=False, db_path=DB_PATH):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if reset:
        from app.models import SCHEMA, ensure_admin

        conn.executescript(
            """
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS items;
            DROP TABLE IF EXISTS suppliers;
            DROP TABLE IF EXISTS stock_items;
            DROP TABLE IF EXISTS market_list;
            DROP TABLE IF EXISTS users;
            """
        )
        conn.executescript(SCHEMA)
        ensure_admin(conn)

    suppliers_existing = conn.execute("SELECT COUNT(*) AS c FROM suppliers").fetchone()["c"]
    if suppliers_existing == 0:
        for name, contact, phone, email, notes in SUPPLIERS:
            full_notes = notes
            if contact:
                full_notes = f"Contato: {contact}. {notes}".strip()
            conn.execute(
                "INSERT INTO suppliers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                (name, phone, email, full_notes),
            )

    supplier_map = {
        row["name"]: row["id"]
        for row in conn.execute("SELECT id, name FROM suppliers").fetchall()
    }

    items_existing = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    if items_existing == 0:
        for supplier_name, name, item_type, item_subtype, unit in ITEMS:
            conn.execute(
                """
                INSERT INTO items (supplier_id, name, item_type, item_subtype, unit)
                VALUES (?, ?, ?, ?, ?)
                """,
                (supplier_map.get(supplier_name), name, item_type, item_subtype, unit),
            )

    stock_existing = conn.execute("SELECT COUNT(*) AS c FROM stock_items").fetchone()["c"]
    if stock_existing == 0:
        for name, unit, qty, low in STOCK:
            conn.execute(
                "INSERT INTO stock_items (name, unit, qty, low_threshold) VALUES (?, ?, ?, ?)",
                (name, unit, qty, low),
            )

    market_existing = conn.execute("SELECT COUNT(*) AS c FROM market_list").fetchone()["c"]
    if market_existing == 0:
        for item, qty, notes in MARKET:
            conn.execute(
                "INSERT INTO market_list (item, qty, notes) VALUES (?, ?, ?)",
                (item, qty, notes),
            )

    orders_existing = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    if orders_existing == 0:
        item_map = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM items").fetchall()
        }
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for supplier_name, item_name, qty, status, total in ORDERS:
            conn.execute(
                """
                INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    supplier_map.get(supplier_name),
                    item_map.get(item_name),
                    qty,
                    status,
                    total,
                    today,
                ),
            )

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Apaga o data.db e recria o esquema antes de inserir dados.",
    )
    args = parser.parse_args()
    seed_db(reset=args.reset)
    print("Seed concluido.")


if __name__ == "__main__":
    main()
