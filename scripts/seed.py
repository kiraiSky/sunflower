import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta


DB_PATH = "data.db"


SUPPLIERS = [
    ("Delta Cafe", "+351 961 578 259", "", "Cafe, cha e afins."),
    ("Superbock", "+351 961 130 605", "", "Bebidas."),
    ("Garrafeira Rui Vinhos", "+351 915 321 808", "", "Vinhos."),
    ("Papel Pak", "+351 960 000 001", "", "Consumiveis e embalagens."),
    ("Fernando Fernandes", "+351 960 000 002", "", "Descartaveis e limpeza."),
    ("Pro Gel Cone", "+351 912 851 503", "", "Detergentes."),
    ("Bio F.F", "+351 960 000 003", "", "Higiene e desinfeccao."),
    ("Mercado", "", "", "Compras locais de apoio diario."),
    ("A ti Marquinhas (Docaria)", "", "", "Sobremesas e docaria."),
    ("Ola", "", "", "Gelados e toppings."),
    ("Aviludo", "", "", "Produtos alimentares e bar."),
    ("Delta", "", "", "Cafe, acucar e adocante."),
]

MARKET_CATALOG = [
    ("Tomate", "Legumes e Verduras", "Armazem", "kg"),
    ("Cebola", "Legumes e Verduras", "Armazem", "kg"),
    ("Alho", "Legumes e Verduras", "Armazem", "kg"),
    ("Batata", "Legumes e Verduras", "Armazem", "kg"),
    ("Cenoura", "Legumes e Verduras", "Armazem", "kg"),
    ("Curgete", "Legumes e Verduras", "Armazem", "kg"),
    ("Beringela", "Legumes e Verduras", "Armazem", "kg"),
    ("Pimento Verde", "Legumes e Verduras", "Armazem", "kg"),
    ("Pimento Vermelho", "Legumes e Verduras", "Armazem", "kg"),
    ("Alface", "Legumes e Verduras", "Armazem", "un"),
    ("Rucula", "Legumes e Verduras", "Armazem", "un"),
    ("Espinafres", "Legumes e Verduras", "Armazem", "kg"),
    ("Cogumelos Frescos", "Legumes e Verduras", "Armazem", "kg"),
    ("Brocolos", "Legumes e Verduras", "Armazem", "kg"),
    ("Couve Flor", "Legumes e Verduras", "Armazem", "kg"),
    ("Pepino", "Legumes e Verduras", "Armazem", "kg"),
    ("Lima", "Frutas", "Armazem", "kg"),
    ("Laranja", "Frutas", "Armazem", "kg"),
    ("Maca", "Frutas", "Armazem", "kg"),
    ("Pera", "Frutas", "Armazem", "kg"),
    ("Banana", "Frutas", "Armazem", "kg"),
    ("Morango", "Frutas", "Armazem", "kg"),
    ("Abacaxi", "Frutas", "Armazem", "un"),
    ("Maracuja", "Frutas", "Armazem", "kg"),
    ("Framboesa", "Frutas", "Armazem", "kg"),
    ("Mirtilo", "Frutas", "Armazem", "kg"),
    ("Manga", "Frutas", "Armazem", "kg"),
    ("Abacate", "Frutas", "Armazem", "kg"),
    ("Salsa", "Mercearia", "Armazem", "un"),
    ("Coentros", "Mercearia", "Armazem", "un"),
    ("Cebolinho", "Mercearia", "Armazem", "un"),
    ("Manjericao", "Mercearia", "Armazem", "un"),
    ("Alecrim", "Mercearia", "Armazem", "un"),
    ("Louro", "Mercearia", "Armazem", "un"),
    ("Oreganos", "Mercearia", "Despensa", "un"),
    ("Canela em Po", "Mercearia", "Despensa", "un"),
    ("Cominhos", "Mercearia", "Despensa", "un"),
    ("Paprica Doce", "Mercearia", "Despensa", "un"),
    ("Pimenta Preta", "Mercearia", "Despensa", "un"),
    ("Noz Moscada", "Mercearia", "Despensa", "un"),
    ("Vinagre Balsamico", "Mercearia", "Despensa", "un"),
    ("Azeite Virgem Extra", "Mercearia", "Despensa", "un"),
]

REQUESTED_CATALOG = [
    ("Mercado", "Alfinete", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Agrafos", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Caneta esferografica", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Caneta Marcador", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Corretor", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Papel A4", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Rebucados", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Palito de dente", "Bar", "Diversos do bar", "un"),
    ("Mercado", "Baloes", "Bar", "festas/eventos", "un"),
    ("Mercado", "Confetes", "Bar", "festas/eventos", "un"),
    ("Mercado", "Velas de aniversario", "Bar", "festas/eventos", "un"),
    ("Mercado", "Maca", "Frutas", "Frutas", "kg"),
    ("Mercado", "Laranja", "Frutas", "Frutas", "kg"),
    ("Mercado", "Banana", "Frutas", "Frutas", "kg"),
    ("Mercado", "Ananas/Abacaxi", "Frutas", "Frutas", "un"),
    ("Mercado", "Manga", "Frutas", "Frutas", "kg"),
    ("Mercado", "Frutos Silvestres", "Frutas", "Frutas", "kg"),
    ("Mercado", "Lima", "Frutas", "Frutas", "kg"),
    ("Mercado", "Limao", "Frutas", "Frutas", "kg"),
    ("Mercado", "Maca Reineta", "Frutas", "Frutas", "kg"),
    ("Mercado", "Cachaca", "Bar", "Cocktails", "un"),
    ("Mercado", "Acucar Marrom/Mascavo", "Bar", "Cocktails", "kg"),
    ("Mercado", "Vodka", "Bar", "Cocktails", "un"),
    ("Mercado", "Licor Tia Maria", "Bar", "Cocktails", "un"),
    ("Mercado", "Prosecco/Espumante", "Bar", "Cocktails", "un"),
    ("Mercado", "Elderflower", "Bar", "Cocktails", "un"),
    ("Mercado", "Hortela", "Bar", "Cocktails", "un"),
    ("Mercado", "Gin", "Bar", "Cocktails", "un"),
    ("Mercado", "Lillet Blanc", "Bar", "Cocktails", "un"),
    ("Mercado", "Sumo de limao", "Bar", "Cocktails", "un"),
    ("Mercado", "Monin Maracuja", "Bar", "Cocktails", "un"),
    ("Mercado", "Bitters", "Bar", "Cocktails", "un"),
    ("Mercado", "Peach Schnapps", "Bar", "Cocktails", "un"),
    ("Mercado", "Xarope de Groselha", "Bar", "Cocktails", "un"),
    ("Mercado", "Bacardi Rum", "Bar", "Cocktails", "un"),
    ("Mercado", "Jameson", "Bar", "Cocktails", "un"),
    ("Mercado", "Gelo picado", "Bar", "Cocktails", "kg"),
    ("Mercado", "Gelo cubo", "Bar", "Cocktails", "kg"),
    ("Mercado", "Canela", "Bar", "Cocktails", "un"),
    ("Mercado", "Palinhas altas", "Bar", "Cocktails", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de Maca", "Sobremesas", "Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de Alfarroba e Laranja", "Sobremesas", "Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Cheesecake de frutos silvestres", "Sobremesas", "Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Banoffee", "Sobremesas", "Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de brigadeiro", "Sobremesas", "Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de batata doce", "Sobremesas", "Sobremesas", "un"),
    ("Mercado", "Chantilly", "Sobremesas", "Sobremesas", "un"),
    ("Mercado", "Morangos", "Sobremesas", "Sobremesas", "kg"),
    ("Mercado", "Chocolate em po", "Sobremesas", "Sobremesas", "kg"),
    ("Mercado", "Cacau em po", "Sobremesas", "Sobremesas", "kg"),
    ("Mercado", "Acucar de confeiteiro", "Sobremesas", "Sobremesas", "kg"),
    ("Ola", "Topping Chocolate", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Topping Morango", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Topping Caramelo", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Gelado Morango", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Gelado Baunilha", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Gelado Caramelo", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Gelado Sorbet Limao", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Gelado Chocolate", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Magnum Pessego", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Magnum Pistachio", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Magnum Amendoas", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Double Gold Billionaire", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Magnum Sandwich", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Caramel & Nuts", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Magnum Chocolate Branco", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Pistachio", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Tropical Manga", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Chocnball", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Morango", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Brigadeiro", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cornetto Classico", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Remix cpploe", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Volcanny", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Filipinos", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Rol", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Perna de Pau", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Cone Perna de Pau", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Twister", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Calippo Morango", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Calippo Limao", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Solero Exotico", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Solero Morango e lima", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Picolero", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Fizz", "Sobremesas", "Sobremesas", "un"),
    ("Ola", "Haribo push up", "Sobremesas", "Sobremesas", "un"),
    ("Aviludo", "Canela", "Sobremesas", "Sobremesas", "un"),
    ("Aviludo", "Manteiga mimosa pequena", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Pate de Sardinha Uli", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Azeite Extra Virgem Maduro Oliveira da Serra", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Vinagre Vinho Branco Oliveira da Serra", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Ketchup Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Maionese Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Mostarda Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Delta", "Cafe Gold", "Cafetaria", "Cafetaria", "kg"),
    ("Delta", "Acucar", "Cafetaria", "Cafetaria", "kg"),
    ("Delta", "Adocante", "Cafetaria", "Cafetaria", "un"),
]


STOCK = [
    ("Rolo de cozinha", "un", 8, 4),
    ("Papel higienico", "cx", 2, 3),
    ("Detergente", "un", 4, 2),
    ("Toalitas de limao", "cx", 1, 2),
]


def _today(days_ago=0):
    return (date.today() - timedelta(days=days_ago)).isoformat()


# supplier_name, item_name, qty, status, total, ordered_at
ORDERS = [
    ("Delta Cafe", "Cafe Grao", 8, "ordered", 120.0, _today(6)),
    ("Garrafeira Rui Vinhos", "Esteva Tinto", 12, "pending", 210.0, _today(2)),
    ("Papel Pak", "Rolos Termicos", 6, "ordered", 36.0, _today(7)),
    ("Fernando Fernandes", "Sacos de Lixo 50L", 10, "pending", 85.0, _today(1)),
    ("Mercado", "Limoes Frescos", 1, "purchased", 0.0, _today(1)),
    ("Mercado", "Hortela Fresca", 2, "pending", 0.0, _today(0)),
    ("Mercado", "Gelo Saco 2kg", 3, "pending", 0.0, _today(0)),
    ("Mercado", "Guardanapos Bar", 4, "pending", 0.0, _today(2)),
]


def seed_db(reset=False, db_path=DB_PATH):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from app.models import SCHEMA, ensure_admin, migrate_db

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if reset:
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
        migrate_db(conn)
        ensure_admin(conn)
    else:
        migrate_db(conn)

    existing_supplier_names = {
        row["name"].strip().lower() for row in conn.execute("SELECT name FROM suppliers").fetchall()
    }
    for name, phone, email, notes in SUPPLIERS:
        if name.strip().lower() in existing_supplier_names:
            continue
        conn.execute(
            "INSERT INTO suppliers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
            (name, phone, email, notes),
        )
        existing_supplier_names.add(name.strip().lower())

    supplier_map = {
        row["name"]: row["id"]
        for row in conn.execute("SELECT id, name FROM suppliers").fetchall()
    }

    items_existing = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    if items_existing == 0:
        for supplier_name, name, item_type, item_subtype, unit in ITEMS:
            conn.execute(
                """
                INSERT INTO items (supplier_id, name, item_type, item_subtype, unit, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (supplier_map.get(supplier_name), name, item_type, item_subtype, unit),
            )

    # Ensure requested catalog items exist even on non-empty databases.
    existing_item_keys = {
        (
            row["supplier_id"],
            row["name"].strip().lower(),
            row["item_type"].strip().lower(),
            row["item_subtype"].strip().lower(),
            row["unit"].strip().lower(),
        )
        for row in conn.execute(
            "SELECT supplier_id, name, item_type, item_subtype, unit FROM items"
        ).fetchall()
    }
    requested_rows = [("Mercado", *row) for row in MARKET_CATALOG] + REQUESTED_CATALOG
    for supplier_name, name, item_type, item_subtype, unit in requested_rows:
        supplier_id = supplier_map.get(supplier_name)
        if not supplier_id:
            continue
        key = (
            supplier_id,
            name.strip().lower(),
            item_type.strip().lower(),
            item_subtype.strip().lower(),
            unit.strip().lower(),
        )
        if key in existing_item_keys:
            continue
        conn.execute(
            """
            INSERT INTO items (supplier_id, name, item_type, item_subtype, unit, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (supplier_id, name, item_type, item_subtype, unit),
        )
        existing_item_keys.add(key)

    stock_existing = conn.execute("SELECT COUNT(*) AS c FROM stock_items").fetchone()["c"]
    if stock_existing == 0:
        for name, unit, qty, low in STOCK:
            conn.execute(
                "INSERT INTO stock_items (name, unit, qty, low_threshold) VALUES (?, ?, ?, ?)",
                (name, unit, qty, low),
            )

    orders_existing = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    if orders_existing == 0:
        item_map = {
            row["name"]: (row["id"], row["unit"], row["supplier_id"])
            for row in conn.execute("SELECT id, name, unit, supplier_id FROM items").fetchall()
        }
        for supplier_name, item_name, qty, status, total, ordered_at in ORDERS:
            supplier_id = supplier_map.get(supplier_name)
            item_meta = item_map.get(item_name)
            if not supplier_id or not item_meta:
                continue
            item_id, unit, _ = item_meta
            cur = conn.execute(
                """
                INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, item_id, qty, status, total, ordered_at),
            )
            order_id = cur.lastrowid

            # Refined pattern: each Mercado order also creates an explicit market_list event row.
            if supplier_name.lower() == "mercado":
                checked = 1 if status == "purchased" else 0
                purchased_at = ordered_at if checked else None
                qty_text = f"{qty:.2f}".rstrip("0").rstrip(".")
                if unit:
                    qty_text = f"{qty_text} {unit}"
                conn.execute(
                    """
                    INSERT INTO market_list (
                        item, qty, notes, checked,
                        item_id, order_id, qty_value, unit, listed_at, purchased_at
                    )
                    VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_name, qty_text, checked, item_id, order_id, qty, unit, ordered_at, purchased_at),
                )

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Apaga o banco e recria o esquema antes de inserir dados.",
    )
    parser.add_argument(
        "--db-path",
        default=DB_PATH,
        help="Caminho do arquivo .db a ser gerado/preenchido.",
    )
    args = parser.parse_args()
    seed_db(reset=args.reset, db_path=args.db_path)
    print(f"Seed concluido em: {args.db_path}")


if __name__ == "__main__":
    main()
