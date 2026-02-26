import argparse
import os
import sqlite3
import sys


DB_PATH = "data.db"


SUPPLIERS = [
    ("Mercado", "", "", ""),
    ("A ti Marquinhas (Docaria)", "", "", ""),
    ("Ola", "", "", ""),
    ("Aviludo", "", "", ""),
    ("Delta", "", "", ""),
    ("Superbock", "", "", ""),
    ("Garrafeira Rui", "", "", ""),
]


ITEMS = [
    ("Mercado", "Alfinete", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Agrafos", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Caneta esferografica", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Caneta Marcador", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Corretor", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Papel A4", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Rebucados", "Bar", "Diversos Bar", "un"),
    ("Mercado", "Palito de dente", "Bar", "Diversos Bar", "un"),
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
    ("Mercado", "Frutos Silvestres", "Sobremesas", "Sobremesas", "kg"),
    ("Mercado", "Hortela", "Sobremesas", "Sobremesas", "un"),
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
    ("Ola", "Cornetto Chocn'ball", "Sobremesas", "Sobremesas", "un"),
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
    ("Superbock", "Cerveja de garrafa Superbock", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Cerveja de garrafa Stout Superbock", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Cerveja de garrafa sem alcool Superbock", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Coca-cola lata", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Vitalis 75cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Vitalis 1,5l", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Vitalis 33cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua das Pedras 75cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Coca Cola zero Garrafa", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Coca Cola Garrafa", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Sprite Garrafa", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Fanta Laranja Garrafa", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Somersby", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Castelo", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua das Pedras 25cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua das Pedras de limao 25cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Lipton Ice tea Pessego", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Lipton Ice tea Limao", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Lipton Ice tea Manga", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Compal Manga (nectar)", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Compal Manga Laranja (nectar)", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Compal Laranja (nectar)", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Compal Pessego (nectar)", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Compal Maca (nectar)", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Tonica Schweppes 20cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Ucal 25cl", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Barril de cerveja 30L", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Agua Caramulo 6L", "Bebidas", "Bebidas", "un"),
    ("Superbock", "Capataz Tinto 5L", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Capataz Branco 5L", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Mazouco Tinto", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Monte das Servas Tinto", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Monte das Servas Branco", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Planura Tinto", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Rossio Tinto", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Rossio Branco", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Rossio Rose", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Tiago Cabaco .Com Tinto", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Tiago Cabaco .Com Branco", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Tiago Cabaco .Com Rose", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Tiago Cabaco Vinhas Velhas Branco", "Vinhos", "Vinhos", "un"),
    ("Superbock", "Tiago Cabaco Vinhas Velhas Tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Casal Garcia verde", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Quinta de Aveleda verde", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Mateus Rose", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Esteva Tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Cabriz Tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Melange a Trois Tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Monte Fuscaz Rose", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Monte Fuscaz Branco", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Monte Fuscaz Tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Villa Alvor tinto", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "Villa Alvor Branco", "Vinhos", "Vinhos", "un"),
    ("Garrafeira Rui", "BSE Branco", "Vinhos", "Vinhos", "un"),
    ("Mercado", "Cachaca 51", "Alcool", "Alcool", "un"),
    ("Mercado", "Bombay Gin", "Alcool", "Alcool", "un"),
    ("Mercado", "Gordon's Gin", "Alcool", "Alcool", "un"),
    ("Mercado", "Gordon's Pink Gin", "Alcool", "Alcool", "un"),
    ("Mercado", "Bacardi Rum", "Alcool", "Alcool", "un"),
    ("Mercado", "Smirnoff Vodka", "Alcool", "Alcool", "un"),
    ("Mercado", "Tequila", "Alcool", "Alcool", "un"),
    ("Mercado", "Aldeia Velha aguardente", "Alcool", "Alcool", "un"),
    ("Mercado", "Ponte de marante aguardente", "Alcool", "Alcool", "un"),
    ("Mercado", "Castelo Silves aguardadente de medronho", "Alcool", "Alcool", "un"),
    ("Mercado", "Fernet Branca", "Alcool", "Alcool", "un"),
    ("Mercado", "Baileys", "Alcool", "Alcool", "un"),
    ("Mercado", "Berneroy Calvados", "Alcool", "Alcool", "un"),
    ("Mercado", "Cointreau", "Alcool", "Alcool", "un"),
    ("Mercado", "Grand Marnier", "Alcool", "Alcool", "un"),
    ("Mercado", "Malibu", "Alcool", "Alcool", "un"),
    ("Mercado", "Ricard", "Alcool", "Alcool", "un"),
    ("Mercado", "Tia Maria Coffe", "Alcool", "Alcool", "un"),
    ("Mercado", "Licor Beirao", "Alcool", "Alcool", "un"),
    ("Mercado", "Porto Tinto", "Alcool", "Alcool", "un"),
    ("Mercado", "Porto Branco", "Alcool", "Alcool", "un"),
    ("Mercado", "Macieira", "Alcool", "Alcool", "un"),
    ("Mercado", "Dom Ramires", "Alcool", "Alcool", "un"),
    ("Mercado", "Groselha", "Alcool", "Alcool", "un"),
    ("Mercado", "Dom Cristina", "Alcool", "Alcool", "un"),
    ("Mercado", "Captain Morgan Rum", "Alcool", "Alcool", "un"),
    ("Mercado", "Cutty Sark", "Alcool", "Alcool", "un"),
    ("Mercado", "Grants", "Alcool", "Alcool", "un"),
    ("Mercado", "J&B JB", "Alcool", "Alcool", "un"),
    ("Mercado", "J&B 15 anos JB", "Alcool", "Alcool", "un"),
    ("Mercado", "Golden Loch", "Alcool", "Alcool", "un"),
    ("Mercado", "White Horse", "Alcool", "Alcool", "un"),
    ("Mercado", "Ballantines", "Alcool", "Alcool", "un"),
    ("Mercado", "Jack daniels", "Alcool", "Alcool", "un"),
    ("Mercado", "The Famous Grouse", "Alcool", "Alcool", "un"),
    ("Mercado", "Jameson", "Alcool", "Alcool", "un"),
    ("Mercado", "William Lawson", "Alcool", "Alcool", "un"),
    ("Mercado", "Martini Bianco (Branco)", "Alcool", "Alcool", "un"),
    ("Mercado", "Martini Rosso (Roxo)", "Alcool", "Alcool", "un"),
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
            DROP TABLE IF EXISTS todo_order_links;
            DROP TABLE IF EXISTS todo_check_entries;
            DROP TABLE IF EXISTS todo_checks;
            DROP TABLE IF EXISTS todo_catalog;
            DROP TABLE IF EXISTS notices;
            DROP TABLE IF EXISTS market_list;
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS items;
            DROP TABLE IF EXISTS stock_items;
            DROP TABLE IF EXISTS suppliers;
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

    for supplier_name, name, item_type, item_subtype, unit in ITEMS:
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

