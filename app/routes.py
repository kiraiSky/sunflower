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
            flash("Credenciais inválidas", "error")
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
            market = conn.execute("SELECT COUNT(*) FROM market_list WHERE checked = 0").fetchone()[
                0
            ]
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
            item_type = request.form.get("item_type", "").strip()
            item_zone = request.form.get("item_zone", "").strip()
            unit = request.form.get("unit", "").strip()
            new_type = request.form.get("new_item_type", "").strip()
            new_zone = request.form.get("new_item_zone", "").strip()
            new_unit = request.form.get("new_unit", "").strip()

            if new_type:
                item_type = new_type
            if new_zone:
                item_zone = new_zone
            if new_unit:
                unit = new_unit

            with get_db(app) as conn:
                conn.execute(
                    """
                    INSERT INTO items (supplier_id, name, item_type, item_subtype, unit)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        request.form.get("supplier_id") or None,
                        request.form.get("name", "").strip(),
                        item_type,
                        item_zone,
                        unit,
                    ),
                )
            flash("Item criado com sucesso.", "ok")
        supplier_filter = request.args.get("supplier_id", "")
        with get_db(app) as conn:
            suppliers = conn.execute(
                "SELECT id, name FROM suppliers ORDER BY name"
            ).fetchall()
            types = [
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
        show_type = request.args.get("show_type", "0") == "1"
        show_zone = request.args.get("show_zone", "0") == "1"
        show_unit = request.args.get("show_unit", "0") == "1"
        return render_template(
            "items.html",
            user=current_user(),
            suppliers=suppliers,
            items=rows,
            show_list=show_list,
            types=types,
            zones=zones,
            units=units,
            supplier_filter=supplier_filter,
            show_type=show_type,
            show_zone=show_zone,
            show_unit=show_unit,
        )

    @app.route("/items/data")
    def items_data():
        if (redir := login_required()) is not None:
            return redir
        supplier_filter = request.args.get("supplier_id", "")
        with get_db(app) as conn:
            if supplier_filter:
                rows = conn.execute(
                    """
                    SELECT i.id, s.name, s.phone, i.name, i.item_type, i.item_subtype, i.unit
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
                    SELECT i.id, s.name, s.phone, i.name, i.item_type, i.item_subtype, i.unit
                    FROM items i
                    LEFT JOIN suppliers s ON s.id = i.supplier_id
                    ORDER BY i.name
                    """
                ).fetchall()
        data = [
            {
                "id": row[0],
                "supplier": row[1] or "—",
                "phone": row[2] or "—",
                "item": row[3],
                "type": row[4],
                "zone": row[5],
                "unit": row[6],
            }
            for row in rows
        ]
        return jsonify(data)

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
        supplier_filter = request.args.get("supplier_id", "")
        if request.method == "POST":
            with get_db(app) as conn:
                conn.execute(
                    """
                    INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.form.get("supplier_id") or None,
                        request.form.get("item_id") or None,
                        float(request.form.get("qty", "0") or 0),
                        request.form.get("status", "pending").strip(),
                        float(request.form.get("total", "0") or 0),
                        request.form.get("ordered_at") or now_iso(),
                    ),
                )
        with get_db(app) as conn:
            suppliers = conn.execute(
                "SELECT id, name FROM suppliers ORDER BY name"
            ).fetchall()
            if supplier_filter:
                items = conn.execute(
                    """
                    SELECT id, name, item_type, item_subtype
                    FROM items
                    WHERE supplier_id = ?
                    ORDER BY name
                    """,
                    (supplier_filter,),
                ).fetchall()
            else:
                items = conn.execute(
                    """
                    SELECT id, name, item_type, item_subtype
                    FROM items
                    ORDER BY name
                    """
                ).fetchall()
            rows = conn.execute(
                """
                SELECT o.id, s.name, i.name, i.item_type, i.item_subtype, o.qty, o.status, o.total, o.ordered_at
                FROM orders o
                LEFT JOIN suppliers s ON s.id = o.supplier_id
                LEFT JOIN items i ON i.id = o.item_id
                ORDER BY o.ordered_at DESC
                """
            ).fetchall()
        return render_template(
            "orders.html",
            user=current_user(),
            suppliers=suppliers,
            items=items,
            orders=rows,
            supplier_filter=supplier_filter,
        )

    @app.route("/admin/seed", methods=["POST"])
    def admin_seed():
        if (redir := login_required()) is not None:
            return redir
        if session.get("role") != "admin":
            flash("Acesso não autorizado.", "error")
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

    @app.route("/market", methods=["GET", "POST"])
    def market():
        if (redir := login_required()) is not None:
            return redir
        if request.method == "POST":
            with get_db(app) as conn:
                conn.execute(
                    "INSERT INTO market_list (item, qty, notes) VALUES (?, ?, ?)",
                    (
                        request.form.get("item", "").strip(),
                        request.form.get("qty", "").strip(),
                        request.form.get("notes", "").strip(),
                    ),
                )
        with get_db(app) as conn:
            rows = conn.execute(
                """
                SELECT id, item, qty, notes, checked
                FROM market_list
                ORDER BY checked, id DESC
                """
            ).fetchall()
        return render_template("market.html", user=current_user(), market_items=rows)

    @app.route("/market/toggle/<int:item_id>")
    def market_toggle(item_id):
        if (redir := login_required()) is not None:
            return redir
        with get_db(app) as conn:
            cur = conn.execute("SELECT checked FROM market_list WHERE id = ?", (item_id,))
            row = cur.fetchone()
            if row:
                new_value = 0 if row[0] else 1
                conn.execute(
                    "UPDATE market_list SET checked = ? WHERE id = ?",
                    (new_value, item_id),
                )
        return redirect(url_for("market"))
