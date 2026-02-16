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


ITEMS = [
    ("Delta Cafe", "Cafe Grao", "Mercearia", "Despensa", "kg"),
    ("Delta Cafe", "Acucar Branco", "Mercearia", "Despensa", "kg"),
    ("Delta Cafe", "Leite UHT", "Laticinios", "Despensa", "un"),
    ("Superbock", "Cerveja Superbock 33cl", "Bebidas", "Frigorifico de bebidas", "cx"),
    ("Superbock", "Agua Sem Gas 1.5L", "Bebidas", "Adega", "un"),
    ("Garrafeira Rui Vinhos", "Casal Garcia", "Vinhos", "Adega", "cx"),
    ("Garrafeira Rui Vinhos", "Esteva Tinto", "Vinhos", "Adega", "cx"),
    ("Papel Pak", "Rolos Termicos", "Descartaveis", "Armazem", "cx"),
    ("Fernando Fernandes", "Sacos de Lixo 50L", "Descartaveis", "Armazem", "cx"),
    ("Pro Gel Cone", "Detergente Maquina", "Limpeza", "Armazem", "un"),
    ("Bio F.F", "Desinfetante", "Limpeza", "Armazem", "un"),
    ("Mercado", "Limoes Frescos", "Frutas", "Armazem", "kg"),
    ("Mercado", "Hortela Fresca", "Legumes e Verduras", "Armazem", "un"),
    ("Mercado", "Gelo Saco 2kg", "Bebidas", "Armazem", "un"),
    ("Mercado", "Guardanapos Bar", "Descartaveis", "Armazem", "cx"),
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
    ("Mercado", "Alfinete", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Agrafos", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Caneta esferografica", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Caneta Marcador", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Corretor", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Papel A4", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Rebucados", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Palito de dente", "Bar", "Zona Diversos do bar", "un"),
    ("Mercado", "Baloes", "Bar", "Zona festas/eventos", "un"),
    ("Mercado", "Confetes", "Bar", "Zona festas/eventos", "un"),
    ("Mercado", "Velas de aniversario", "Bar", "Zona festas/eventos", "un"),
    ("Mercado", "Maca", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Laranja", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Banana", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Ananas/Abacaxi", "Frutas", "Zona Frutas", "un"),
    ("Mercado", "Manga", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Frutos Silvestres", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Lima", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Limao", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Maca Reineta", "Frutas", "Zona Frutas", "kg"),
    ("Mercado", "Cachaca", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Acucar Marrom/Mascavo", "Bar", "Zona Cocktails", "kg"),
    ("Mercado", "Vodka", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Licor Tia Maria", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Prosecco/Espumante", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Elderflower", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Hortela", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Gin", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Lillet Blanc", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Sumo de limao", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Monin Maracuja", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Bitters", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Peach Schnapps", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Xarope de Groselha", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Bacardi Rum", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Jameson", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Gelo picado", "Bar", "Zona Cocktails", "kg"),
    ("Mercado", "Gelo cubo", "Bar", "Zona Cocktails", "kg"),
    ("Mercado", "Canela", "Bar", "Zona Cocktails", "un"),
    ("Mercado", "Palinhas altas", "Bar", "Zona Cocktails", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de Maca", "Sobremesas", "Zona Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de Alfarroba e Laranja", "Sobremesas", "Zona Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Cheesecake de frutos silvestres", "Sobremesas", "Zona Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Banoffee", "Sobremesas", "Zona Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de brigadeiro", "Sobremesas", "Zona Sobremesas", "un"),
    ("A ti Marquinhas (Docaria)", "Tarte de batata doce", "Sobremesas", "Zona Sobremesas", "un"),
    ("Mercado", "Chantilly", "Sobremesas", "Zona Sobremesas", "un"),
    ("Mercado", "Morangos", "Sobremesas", "Zona Sobremesas", "kg"),
    ("Mercado", "Chocolate em po", "Sobremesas", "Zona Sobremesas", "kg"),
    ("Mercado", "Cacau em po", "Sobremesas", "Zona Sobremesas", "kg"),
    ("Mercado", "Acucar de confeiteiro", "Sobremesas", "Zona Sobremesas", "kg"),
    ("Ola", "Topping Chocolate", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Topping Morango", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Topping Caramelo", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Gelado Morango", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Gelado Baunilha", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Gelado Caramelo", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Gelado Sorbet Limao", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Gelado Chocolate", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Magnum Pessego", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Magnum Pistachio", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Magnum Amendoas", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Double Gold Billionaire", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Magnum Sandwich", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Caramel & Nuts", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Magnum Chocolate Branco", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Pistachio", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Tropical Manga", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Chocnball", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Morango", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Brigadeiro", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cornetto Classico", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Remix cpploe", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Volcanny", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Filipinos", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Rol", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Perna de Pau", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Cone Perna de Pau", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Twister", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Calippo Morango", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Calippo Limao", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Solero Exotico", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Solero Morango e lima", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Picolero", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Fizz", "Sobremesas", "Zona Sobremesas", "un"),
    ("Ola", "Haribo push up", "Sobremesas", "Zona Sobremesas", "un"),
    ("Aviludo", "Canela", "Sobremesas", "Zona Sobremesas", "un"),
    ("Aviludo", "Manteiga mimosa pequena", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Pate de Sardinha Uli", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Azeite Extra Virgem Maduro Oliveira da Serra", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Vinagre Vinho Branco Oliveira da Serra", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Ketchup Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Maionese Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Aviludo", "Mostarda Sache Heinz", "Bar", "Diversos Bar", "un"),
    ("Delta", "Cafe Gold", "Cafetaria", "Zona Cafetaria", "kg"),
    ("Delta", "Acucar", "Cafetaria", "Zona Cafetaria", "kg"),
    ("Delta", "Adocante", "Cafetaria", "Zona Cafetaria", "un"),
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
