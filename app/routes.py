import json
import unicodedata

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from .models import get_db, now_iso
from scripts.seed import seed_db

DEFAULT_ITEM_GROUPS = [
    "Laticinios",
    "Carnes",
    "Peixes e Mariscos",
    "Legumes e Verduras",
    "Frutas",
    "Mercearia",
    "Pastelaria",
    "Bebidas",
    "Vinhos",
    "Congelados",
    "Limpeza",
    "Descartaveis",
]

DEFAULT_ITEM_ZONES = [
    "Adega",
    "Frigorifico de bolos",
    "Frigorifico de bebidas",
    "Frigorifico cinzento escritorio",
    "Frigorifico cinzento cozinha",
    "Frigorifico branco escritorio",
    "Congelador escritorio",
    "Congelador cozinha",
    "Despensa",
    "Armazem",
]

GROUP_TO_SUGGESTED_ZONES = {
    "Vinhos": ["Adega"],
    "Bebidas": ["Frigorifico de bebidas", "Adega"],
    "Laticinios": ["Frigorifico cinzento cozinha", "Frigorifico branco escritorio"],
    "Pastelaria": ["Frigorifico de bolos", "Congelador cozinha"],
    "Congelados": ["Congelador cozinha", "Congelador escritorio"],
}


def normalize_text(value):
    return " ".join((value or "").strip().split())


def norm_key(value):
    text = normalize_text(value).lower()
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def normalize_with_defaults(value, defaults):
    cleaned = normalize_text(value)
    if not cleaned:
        return ""
    key = norm_key(cleaned)
    for option in defaults:
        if norm_key(option) == key:
            return option
    return cleaned[:1].upper() + cleaned[1:]


def normalize_unit(value):
    cleaned = normalize_text(value).lower()
    canonical_units = {
        "kg": "kg",
        "g": "g",
        "l": "l",
        "ml": "ml",
        "cx": "cx",
        "un": "un",
        "pc": "un",
    }
    return canonical_units.get(cleaned, cleaned)


def parse_bool(value, default=None):
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return 1
    if text in {"0", "false", "no", "off"}:
        return 0
    return default


def register_routes(app):
    def current_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        with get_db(app) as conn:
            cur = conn.execute(
                "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
            )
            return cur.fetchone()

    def login_required():
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return None

    def manager_required():
        role = (session.get("role") or "").strip().lower()
        if role not in {"admin", "manager", "gestor"}:
            flash("Acesso nao autorizado.", "error")
            return redirect(url_for("index"))
        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            with get_db(app) as conn:
                cur = conn.execute(
                    "SELECT id, password_hash, role FROM users WHERE username = ?",
                    (username,),
                )
                row = cur.fetchone()
                if row and check_password_hash(row[1], password):
                    session["user_id"] = row[0]
                    session["role"] = row[2]
                    return redirect(url_for("index"))
            flash("Credenciais invalidas", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def index():
        if (redir := login_required()) is not None:
            return redir
        with get_db(app) as conn:
            suppliers = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
            orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            low_stock = conn.execute(
                "SELECT COUNT(*) FROM stock_items WHERE qty <= low_threshold"
            ).fetchone()[0]
            market = conn.execute(
                """
                SELECT COUNT(*)
                FROM market_list ml
                LEFT JOIN items i ON i.id = ml.item_id
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                WHERE ml.checked = 0
                  AND LOWER(COALESCE(s.name, '')) = 'mercado'
                """
            ).fetchone()[0]
        return render_template(
            "index.html",
            user=current_user(),
            suppliers=suppliers,
            orders=orders,
            low_stock=low_stock,
            market=market,
        )

    @app.route("/items", methods=["GET", "POST"])
    def items():
        if (redir := login_required()) is not None:
            return redir

        if request.method == "POST":
            item_name = normalize_text(request.form.get("name", ""))
            item_group = normalize_text(request.form.get("item_group", ""))
            item_zone = normalize_text(request.form.get("item_zone", ""))
            unit = normalize_text(request.form.get("unit", ""))
            new_group = normalize_text(request.form.get("new_item_group", ""))
            new_zone = normalize_text(request.form.get("new_item_zone", ""))
            new_unit = normalize_text(request.form.get("new_unit", ""))
            supplier_id = request.form.get("supplier_id") or None

            if new_group:
                item_group = new_group
            if new_zone:
                item_zone = new_zone
            if new_unit:
                unit = new_unit

            item_group = normalize_with_defaults(item_group, DEFAULT_ITEM_GROUPS)
            item_zone = normalize_with_defaults(item_zone, DEFAULT_ITEM_ZONES)
            unit = normalize_unit(unit)

            if not supplier_id or not item_name or not item_group or not item_zone or not unit:
                flash("Preencha fornecedor, item, grupo, zona e unidade.", "error")
                return redirect(url_for("items"))

            with get_db(app) as conn:
                duplicate = conn.execute(
                    """
                    SELECT name, item_type, item_subtype
                    FROM items
                    WHERE supplier_id = ? AND LOWER(name) = LOWER(?)
                    LIMIT 1
                    """,
                    (supplier_id, item_name),
                ).fetchone()
                if duplicate:
                    flash(
                        f"Item duplicado: {duplicate[0]} ({duplicate[1]} / {duplicate[2]}).",
                        "error",
                    )
                    return redirect(url_for("items"))

                conn.execute(
                    """
                    INSERT INTO items (supplier_id, name, item_type, item_subtype, unit)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (supplier_id, item_name, item_group, item_zone, unit),
                )
            return redirect(
                url_for(
                    "items",
                    created="1",
                    created_name=item_name,
                    created_group=item_group,
                    created_zone=item_zone,
                )
            )

        supplier_filter = request.args.get("supplier_id", "")
        with get_db(app) as conn:
            suppliers = conn.execute("SELECT id, name FROM suppliers ORDER BY name").fetchall()
            groups = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT item_type FROM items WHERE item_type <> '' ORDER BY item_type"
                ).fetchall()
            ]
            zones = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT item_subtype FROM items WHERE item_subtype <> '' ORDER BY item_subtype"
                ).fetchall()
            ]
            units = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT unit FROM items WHERE unit <> '' ORDER BY unit"
                ).fetchall()
            ]

            groups = sorted(set(DEFAULT_ITEM_GROUPS + groups))
            zones = sorted(set(DEFAULT_ITEM_ZONES + zones))

            if supplier_filter:
                rows = conn.execute(
                    """
                    SELECT i.id, s.name, s.phone, i.name, i.item_type, i.item_subtype, i.unit, i.active
                    FROM items i
                    LEFT JOIN suppliers s ON s.id = i.supplier_id
                    WHERE i.supplier_id = ?
                    ORDER BY i.name
                    """,
                    (supplier_filter,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT i.id, s.name, s.phone, i.name, i.item_type, i.item_subtype, i.unit, i.active
                    FROM items i
                    LEFT JOIN suppliers s ON s.id = i.supplier_id
                    ORDER BY i.name
                    """
                ).fetchall()

        show_list = request.args.get("show", "") == "1"
        show_type = request.args.get("show_type", "1") == "1"
        show_zone = request.args.get("show_zone", "1") == "1"
        show_unit = request.args.get("show_unit", "1") == "1"
        show_active = request.args.get("show_active", "1") == "1"
        created = request.args.get("created", "") == "1"
        created_name = request.args.get("created_name", "")
        created_group = request.args.get("created_group", "")
        created_zone = request.args.get("created_zone", "")

        return render_template(
            "items.html",
            user=current_user(),
            suppliers=suppliers,
            items=rows,
            show_list=show_list,
            groups=groups,
            zones=zones,
            units=units,
            supplier_filter=supplier_filter,
            show_type=show_type,
            show_zone=show_zone,
            show_unit=show_unit,
            show_active=show_active,
            group_zone_map=GROUP_TO_SUGGESTED_ZONES,
            created=created,
            created_name=created_name,
            created_group=created_group,
            created_zone=created_zone,
        )

    @app.route("/items/data")
    def items_data():
        if (redir := login_required()) is not None:
            return redir

        supplier_filter = request.args.get("supplier_id", "")
        group_filter = normalize_text(request.args.get("group", ""))
        zone_filter = normalize_text(request.args.get("zone", ""))
        search = normalize_text(request.args.get("search", ""))
        active_filter = request.args.get("active", "")

        where = []
        params = []
        if supplier_filter:
            where.append("i.supplier_id = ?")
            params.append(supplier_filter)
        if group_filter:
            where.append("i.item_type = ?")
            params.append(group_filter)
        if zone_filter:
            where.append("i.item_subtype = ?")
            params.append(zone_filter)
        if search:
            where.append("LOWER(i.name) LIKE ?")
            params.append(f"%{search.lower()}%")

        parsed_active = parse_bool(active_filter)
        if parsed_active is not None:
            where.append("i.active = ?")
            params.append(parsed_active)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        with get_db(app) as conn:
            rows = conn.execute(
                f"""
                SELECT i.id, i.supplier_id, s.name, s.phone, i.name, i.item_type, i.item_subtype, i.unit, i.active
                FROM items i
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                {where_sql}
                ORDER BY i.name
                """,
                tuple(params),
            ).fetchall()

        data = [
            {
                "id": row[0],
                "supplier_id": row[1],
                "supplier": row[2] or "-",
                "phone": row[3] or "-",
                "item": row[4],
                "group": row[5],
                "zone": row[6],
                "unit": row[7],
                "active": row[8],
            }
            for row in rows
        ]
        return jsonify(data)

    @app.route("/items/check-duplicate")
    def items_check_duplicate():
        if (redir := login_required()) is not None:
            return redir

        supplier_id = request.args.get("supplier_id")
        item_name = normalize_text(request.args.get("name", ""))
        exclude_id = request.args.get("exclude_id")
        if not supplier_id or not item_name:
            return jsonify({"exists": False})

        with get_db(app) as conn:
            params = [supplier_id, item_name]
            extra_where = ""
            if exclude_id:
                extra_where = " AND id <> ?"
                params.append(exclude_id)

            row = conn.execute(
                f"""
                SELECT id, name, item_type, item_subtype
                FROM items
                WHERE supplier_id = ? AND LOWER(name) = LOWER(?) {extra_where}
                LIMIT 1
                """,
                tuple(params),
            ).fetchone()

        if not row:
            return jsonify({"exists": False})

        return jsonify(
            {
                "exists": True,
                "item": {
                    "id": row[0],
                    "name": row[1],
                    "group": row[2],
                    "zone": row[3],
                },
            }
        )

    @app.route("/items/<int:item_id>", methods=["POST"])
    def items_update(item_id):
        if (redir := login_required()) is not None:
            return redir

        payload = request.get_json(silent=True) or {}
        updates = {}

        if "group" in payload:
            updates["item_type"] = normalize_with_defaults(payload.get("group"), DEFAULT_ITEM_GROUPS)
        if "zone" in payload:
            updates["item_subtype"] = normalize_with_defaults(payload.get("zone"), DEFAULT_ITEM_ZONES)
        if "unit" in payload:
            updates["unit"] = normalize_unit(payload.get("unit"))
        if "active" in payload:
            updates["active"] = parse_bool(payload.get("active"), default=1)

        invalid_values = [value for value in updates.values() if value in {"", None}]
        if invalid_values:
            return jsonify({"ok": False, "error": "Campos invalidos."}), 400
        if not updates:
            return jsonify({"ok": False, "error": "Sem alteracoes."}), 400

        set_sql = ", ".join(f"{column} = ?" for column in updates.keys())
        params = list(updates.values()) + [item_id]

        with get_db(app) as conn:
            conn.execute(f"UPDATE items SET {set_sql} WHERE id = ?", tuple(params))

        return jsonify({"ok": True})

    @app.route("/items/bulk-update", methods=["POST"])
    def items_bulk_update():
        if (redir := login_required()) is not None:
            return redir

        payload = request.get_json(silent=True) or {}
        item_ids = payload.get("ids") or []
        if not item_ids:
            return jsonify({"ok": False, "error": "Nenhum item selecionado."}), 400

        updates = {}
        if "group" in payload and normalize_text(payload.get("group", "")):
            updates["item_type"] = normalize_with_defaults(payload.get("group"), DEFAULT_ITEM_GROUPS)
        if "zone" in payload and normalize_text(payload.get("zone", "")):
            updates["item_subtype"] = normalize_with_defaults(payload.get("zone"), DEFAULT_ITEM_ZONES)
        if "unit" in payload and normalize_text(payload.get("unit", "")):
            updates["unit"] = normalize_unit(payload.get("unit"))
        if "active" in payload and str(payload.get("active", "")).strip() != "":
            updates["active"] = parse_bool(payload.get("active"), default=1)

        if not updates:
            return jsonify({"ok": False, "error": "Sem alteracoes para aplicar."}), 400

        placeholders = ", ".join("?" for _ in item_ids)
        set_sql = ", ".join(f"{column} = ?" for column in updates.keys())
        params = list(updates.values()) + item_ids

        with get_db(app) as conn:
            conn.execute(
                f"UPDATE items SET {set_sql} WHERE id IN ({placeholders})",
                tuple(params),
            )

        return jsonify({"ok": True, "updated": len(item_ids)})

    @app.route("/suppliers", methods=["GET", "POST"])
    def suppliers():
        if (redir := login_required()) is not None:
            return redir
        if request.method == "POST":
            with get_db(app) as conn:
                conn.execute(
                    "INSERT INTO suppliers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                    (
                        request.form.get("name", "").strip(),
                        request.form.get("phone", "").strip(),
                        request.form.get("email", "").strip(),
                        request.form.get("notes", "").strip(),
                    ),
                )
        with get_db(app) as conn:
            rows = conn.execute(
                "SELECT id, name, phone, email, notes FROM suppliers ORDER BY name"
            ).fetchall()
        return render_template("suppliers.html", user=current_user(), suppliers=rows)

    @app.route("/orders", methods=["GET", "POST"])
    def orders():
        if (redir := login_required()) is not None:
            return redir

        if request.method == "POST":
            ordered_at = request.form.get("ordered_at") or now_iso()
            raw_selected_items = (request.form.get("selected_items") or "").strip()

            selected_payload = []
            if raw_selected_items:
                try:
                    parsed = json.loads(raw_selected_items)
                except json.JSONDecodeError:
                    parsed = []
                if isinstance(parsed, list):
                    selected_payload = parsed

            if not selected_payload:
                item_id_fallback = request.form.get("item_id")
                qty_raw_fallback = request.form.get("qty", "1")
                if item_id_fallback:
                    selected_payload = [{"item_id": item_id_fallback, "qty": qty_raw_fallback}]

            normalized_items = []
            for entry in selected_payload:
                if not isinstance(entry, dict):
                    continue
                item_id = entry.get("item_id")
                qty_raw = entry.get("qty", 1)
                try:
                    item_id = int(item_id)
                    qty = float(qty_raw)
                except (TypeError, ValueError):
                    continue
                if qty <= 0:
                    continue
                normalized_items.append({"item_id": item_id, "qty": qty})

            if not normalized_items:
                flash("Selecione pelo menos um item valido.", "error")
                return redirect(url_for("orders"))

            merged_by_item = {}
            for entry in normalized_items:
                item_id = entry["item_id"]
                merged_by_item[item_id] = merged_by_item.get(item_id, 0) + entry["qty"]

            with get_db(app) as conn:
                placeholders = ", ".join("?" for _ in merged_by_item.keys())
                item_rows = conn.execute(
                    f"""
                    SELECT i.id, i.supplier_id, i.name, COALESCE(s.name, ''), COALESCE(i.unit, '')
                    FROM items i
                    LEFT JOIN suppliers s ON s.id = i.supplier_id
                    WHERE i.id IN ({placeholders})
                    """,
                    tuple(merged_by_item.keys()),
                ).fetchall()
                item_lookup = {row[0]: row for row in item_rows}

                processed_count = 0
                for item_id, qty in merged_by_item.items():
                    item_row = item_lookup.get(item_id)
                    if not item_row:
                        continue

                    supplier_id = item_row[1]
                    item_name = item_row[2]
                    supplier_name = normalize_text(item_row[3]).lower()
                    item_unit = normalize_text(item_row[4])

                    is_market_supplier = supplier_name == "mercado"

                    if is_market_supplier:
                        cur = conn.execute(
                            """
                            INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (supplier_id, item_id, qty, "pending", 0, ordered_at),
                        )
                        order_id = cur.lastrowid
                        qty_text = f"{qty:.2f}".rstrip("0").rstrip(".")
                        if item_unit:
                            qty_text = f"{qty_text} {item_unit}"
                        conn.execute(
                            """
                            INSERT INTO market_list (item, qty, notes, checked, item_id, order_id, qty_value, unit, listed_at, purchased_at)
                            VALUES (?, ?, '', 0, ?, ?, ?, ?, ?, NULL)
                            """,
                            (item_name, qty_text, item_id, order_id, qty, item_unit, ordered_at),
                        )
                        processed_count += 1
                        continue

                    pending_row = conn.execute(
                        """
                        SELECT id
                        FROM orders
                        WHERE item_id = ? AND status = 'pending'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (item_id,),
                    ).fetchone()

                    if pending_row:
                        conn.execute(
                            """
                            UPDATE orders
                            SET qty = qty + ?, ordered_at = ?
                            WHERE id = ?
                            """,
                            (qty, ordered_at, pending_row[0]),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (supplier_id, item_id, qty, "pending", 0, ordered_at),
                        )
                    processed_count += 1

                if processed_count == 0:
                    flash("Nenhum item valido foi processado.", "error")
                elif processed_count == 1:
                    flash("1 item adicionado/atualizado na lista pendente.", "ok")
                else:
                    flash(f"{processed_count} itens adicionados/atualizados na lista pendente.", "ok")
            return redirect(url_for("orders"))

        with get_db(app) as conn:
            items = conn.execute(
                """
                SELECT
                    i.id,
                    i.name,
                    COALESCE(s.name, '-') AS supplier_name,
                    i.item_type,
                    i.item_subtype,
                    MAX(o.ordered_at) AS last_ordered_at,
                    MAX(CASE WHEN ml.checked = 1 THEN COALESCE(ml.purchased_at, ml.listed_at) ELSE NULL END) AS last_purchased_at
                FROM items i
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                LEFT JOIN orders o ON o.item_id = i.id
                LEFT JOIN market_list ml ON ml.item_id = i.id
                WHERE i.active = 1
                  AND i.id NOT IN (
                    SELECT item_id
                    FROM orders
                    WHERE status = 'pending' AND item_id IS NOT NULL
                  )
                GROUP BY i.id, i.name, s.name, i.item_type, i.item_subtype
                ORDER BY
                  CASE WHEN MAX(o.ordered_at) IS NULL THEN 1 ELSE 0 END,
                  MAX(o.ordered_at) DESC,
                  i.name
                """
            ).fetchall()

            rows = conn.execute(
                """
                SELECT
                    o.id,
                    COALESCE(s.name, '-'),
                    COALESCE(i.name, '-'),
                    o.qty,
                    o.ordered_at
                FROM orders o
                LEFT JOIN items i ON i.id = o.item_id
                LEFT JOIN suppliers s ON s.id = COALESCE(o.supplier_id, i.supplier_id)
                WHERE o.status = 'pending'
                ORDER BY o.ordered_at DESC, o.id DESC
                """
            ).fetchall()

        return render_template(
            "orders.html",
            user=current_user(),
            items=items,
            orders=rows,
        )

    @app.route("/orders/manage", methods=["GET", "POST"])
    def orders_manage():
        if (redir := login_required()) is not None:
            return redir
        if (redir := manager_required()) is not None:
            return redir

        selected_supplier_id = request.args.get("supplier_id", "").strip()
        action = ""

        if request.method == "POST":
            action = (request.form.get("action") or "").strip()
            selected_supplier_id = (request.form.get("supplier_id") or "").strip()

            if action == "mark_sent":
                if not selected_supplier_id:
                    flash("Fornecedor invalido.", "error")
                    return redirect(url_for("orders_manage"))
                try:
                    selected_supplier_id_int = int(selected_supplier_id)
                except ValueError:
                    flash("Fornecedor invalido.", "error")
                    return redirect(url_for("orders_manage"))

                with get_db(app) as conn:
                    cur = conn.execute(
                        """
                        UPDATE orders
                        SET status = 'sent'
                        WHERE status = 'pending'
                          AND COALESCE(supplier_id, (
                            SELECT supplier_id FROM items WHERE items.id = orders.item_id
                          )) = ?
                        """,
                        (selected_supplier_id_int,),
                    )
                if cur.rowcount > 0:
                    flash(f"{cur.rowcount} item(ns) marcado(s) como enviado(s).", "ok")
                else:
                    flash("Nenhum item pendente foi atualizado para este fornecedor.", "error")
                return redirect(url_for("orders_manage"))

        with get_db(app) as conn:
            rows = conn.execute(
                """
                SELECT
                    o.id,
                    COALESCE(s.id, i.supplier_id) AS supplier_id,
                    COALESCE(s.name, 'Sem fornecedor') AS supplier_name,
                    COALESCE(i.name, 'Item sem nome') AS item_name,
                    o.qty,
                    COALESCE(i.unit, '') AS unit,
                    o.ordered_at
                FROM orders o
                LEFT JOIN items i ON i.id = o.item_id
                LEFT JOIN suppliers s ON s.id = COALESCE(o.supplier_id, i.supplier_id)
                WHERE o.status = 'pending'
                ORDER BY supplier_name, i.name, o.id DESC
                """
            ).fetchall()

        grouped = {}
        for row in rows:
            supplier_id = str(row[1] or "")
            if supplier_id not in grouped:
                grouped[supplier_id] = {
                    "supplier_id": supplier_id,
                    "supplier_name": row[2],
                    "orders": [],
                }
            grouped[supplier_id]["orders"].append(
                {
                    "order_id": row[0],
                    "item_name": row[3],
                    "qty": row[4],
                    "unit": row[5],
                    "ordered_at": row[6],
                }
            )

        groups = list(grouped.values())
        groups.sort(key=lambda g: g["supplier_name"].lower())

        message_text = ""
        selected_group = None
        if selected_supplier_id:
            selected_group = next(
                (g for g in groups if g["supplier_id"] == selected_supplier_id),
                None,
            )
            if selected_group:
                lines = [
                    "Bom dia, quero fazer uma encomenda pro restaurante Girassol em Quarteira, preciso dos seguintes itens:"
                ]
                for order in selected_group["orders"]:
                    qty = f"{order['qty']:.2f}".rstrip("0").rstrip(".")
                    unit = f" {order['unit']}".rstrip() if order["unit"] else ""
                    lines.append(f"- {order['item_name']}: {qty}{unit}")
                message_text = "\n".join(lines)

        return render_template(
            "orders_manage.html",
            user=current_user(),
            groups=groups,
            selected_supplier_id=selected_supplier_id,
            selected_group=selected_group,
            message_text=message_text,
        )

    @app.route("/admin/seed", methods=["POST"])
    def admin_seed():
        if (redir := login_required()) is not None:
            return redir
        if session.get("role") != "admin":
            flash("Acesso nao autorizado.", "error")
            return redirect(url_for("index"))
        seed_db(reset=True, db_path=app.config["DATABASE"])
        flash("Dados de teste repostos.", "ok")
        return redirect(url_for("index"))

    @app.route("/stock", methods=["GET", "POST"])
    def stock():
        if (redir := login_required()) is not None:
            return redir
        if request.method == "POST":
            with get_db(app) as conn:
                conn.execute(
                    """
                    INSERT INTO stock_items (name, unit, qty, low_threshold)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.form.get("name", "").strip(),
                        request.form.get("unit", "").strip(),
                        float(request.form.get("qty", "0") or 0),
                        float(request.form.get("low_threshold", "0") or 0),
                    ),
                )
        with get_db(app) as conn:
            rows = conn.execute(
                """
                SELECT id, name, unit, qty, low_threshold
                FROM stock_items
                ORDER BY name
                """
            ).fetchall()
        return render_template("stock.html", user=current_user(), stock_items=rows)

    @app.route("/market")
    def market():
        if (redir := login_required()) is not None:
            return redir
        with get_db(app) as conn:
            conn.execute(
                """
                INSERT INTO market_list (item, qty, notes, checked, item_id, order_id, qty_value, unit, listed_at, purchased_at)
                SELECT
                    COALESCE(i.name, 'Item sem nome'),
                    CASE
                      WHEN COALESCE(i.unit, '') <> '' THEN TRIM(CAST(o.qty AS TEXT) || ' ' || i.unit)
                      ELSE CAST(o.qty AS TEXT)
                    END,
                    '',
                    CASE WHEN o.status = 'purchased' THEN 1 ELSE 0 END,
                    o.item_id,
                    o.id,
                    o.qty,
                    COALESCE(i.unit, ''),
                    o.ordered_at,
                    CASE WHEN o.status = 'purchased' THEN o.ordered_at ELSE NULL END
                FROM orders o
                LEFT JOIN items i ON i.id = o.item_id
                LEFT JOIN suppliers s ON s.id = COALESCE(o.supplier_id, i.supplier_id)
                WHERE LOWER(COALESCE(s.name, '')) = 'mercado'
                  AND NOT EXISTS (
                    SELECT 1 FROM market_list ml WHERE ml.order_id = o.id
                  )
                """
            )
            rows = conn.execute(
                """
                SELECT
                    ml.id,
                    COALESCE(i.name, ml.item, 'Item sem nome') AS item_name,
                    COALESCE(ml.qty_value, 0) AS qty_value,
                    COALESCE(ml.unit, '') AS unit,
                    COALESCE(ml.listed_at, '') AS listed_at,
                    ml.checked,
                    ml.order_id
                FROM market_list ml
                LEFT JOIN items i ON i.id = ml.item_id
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                WHERE LOWER(COALESCE(s.name, '')) = 'mercado'
                ORDER BY
                    ml.checked ASC,
                    COALESCE(ml.listed_at, '') DESC,
                    ml.id DESC
                """
            ).fetchall()
        missing_items = [row for row in rows if row[5] == 0]
        purchased_items = [row for row in rows if row[5] == 1]
        return render_template(
            "market.html",
            user=current_user(),
            missing_items=missing_items,
            purchased_items=purchased_items,
        )

    @app.route("/market/toggle/<int:entry_id>")
    def market_toggle(entry_id):
        if (redir := login_required()) is not None:
            return redir
        with get_db(app) as conn:
            cur = conn.execute(
                """
                SELECT ml.checked, ml.order_id
                FROM market_list ml
                LEFT JOIN items i ON i.id = ml.item_id
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                WHERE ml.id = ?
                  AND LOWER(COALESCE(s.name, '')) = 'mercado'
                """,
                (entry_id,),
            )
            row = cur.fetchone()
            if row:
                checked = int(row[0] or 0)
                order_id = row[1]
                new_checked = 0 if checked else 1
                purchased_at = now_iso() if new_checked else None
                conn.execute(
                    """
                    UPDATE market_list
                    SET checked = ?, purchased_at = ?
                    WHERE id = ?
                    """,
                    (new_checked, purchased_at, entry_id),
                )
                if order_id:
                    new_status = "purchased" if new_checked else "pending"
                    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        return redirect(url_for("market"))
