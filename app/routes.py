import json
import re
import unicodedata
from datetime import datetime, timezone

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

DEFAULT_TODO_AREAS = {
    "bar": "Bar",
    "cozinha": "Cozinha",
}


def normalize_text(value):
    return " ".join((value or "").strip().split())


def norm_key(value):
    text = normalize_text(value).lower()
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def build_todo_area_key(value):
    key = re.sub(r"[^a-z0-9]+", "_", norm_key(value)).strip("_")
    if not key:
        return ""
    if key[0].isdigit():
        key = f"a_{key}"
    return key


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

    def get_todo_area_labels(conn):
        rows = conn.execute(
            """
            SELECT area_key, area_label
            FROM todo_areas
            WHERE active = 1
            ORDER BY area_label
            """
        ).fetchall()
        if rows:
            return {row[0]: row[1] for row in rows}
        return DEFAULT_TODO_AREAS.copy()

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
        notices = []
        notices_new_count = 0
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
            notice_rows = conn.execute(
                """
                SELECT id, text, created_at
                FROM notices
                ORDER BY created_at DESC, id DESC
                LIMIT 8
                """
            ).fetchall()

        today = datetime.now(timezone.utc).date()
        for row in notice_rows:
            created_date = None
            try:
                created_date = datetime.strptime((row[2] or "").strip(), "%Y-%m-%d").date()
            except ValueError:
                pass
            is_new = bool(
                created_date
                and 0 <= (today - created_date).days < 3
            )
            if is_new:
                notices_new_count += 1
            notices.append(
                {
                    "id": row[0],
                    "text": row[1],
                    "created_at": created_date.strftime("%d/%m/%Y") if created_date else (row[2] or ""),
                    "is_new": is_new,
                }
            )

        role = (session.get("role") or "").strip().lower()
        can_add_notices = role in {"admin", "manager", "gestor"}

        return render_template(
            "index.html",
            user=current_user(),
            suppliers=suppliers,
            orders=orders,
            low_stock=low_stock,
            market=market,
            notices=notices,
            notices_new_count=notices_new_count,
            can_add_notices=can_add_notices,
            can_manage_notices=can_add_notices,
        )

    @app.route("/notices", methods=["POST"])
    def notices_add():
        if (redir := login_required()) is not None:
            return redir

        role = (session.get("role") or "").strip().lower()
        if role not in {"admin", "manager", "gestor"}:
            flash("Apenas gestores podem criar avisos.", "error")
            return redirect(url_for("index"))

        text = normalize_text(request.form.get("text", ""))
        if not text:
            flash("Escreva um aviso antes de guardar.", "error")
            return redirect(url_for("index"))
        if len(text) > 220:
            flash("O aviso pode ter no maximo 220 caracteres.", "error")
            return redirect(url_for("index"))

        with get_db(app) as conn:
            conn.execute(
                "INSERT INTO notices (text, created_at, created_by) VALUES (?, ?, ?)",
                (text, now_iso(), session.get("user_id")),
            )
        flash("Aviso adicionado.", "ok")
        return redirect(url_for("index"))

    @app.route("/notices/<int:notice_id>/delete", methods=["POST"])
    def notices_delete(notice_id):
        if (redir := login_required()) is not None:
            return redir

        role = (session.get("role") or "").strip().lower()
        if role not in {"admin", "manager", "gestor"}:
            return jsonify({"ok": False, "error": "Acesso nao autorizado."}), 403

        with get_db(app) as conn:
            cur = conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
            if cur.rowcount == 0:
                return jsonify({"ok": False, "error": "Aviso nao encontrado."}), 404

        return jsonify({"ok": True})

    @app.route("/todo/catalog/manage", methods=["POST"])
    def todo_catalog_manage():
        if (redir := login_required()) is not None:
            return redir
        if (redir := manager_required()) is not None:
            return redir

        with get_db(app) as conn:
            area_labels = get_todo_area_labels(conn)
            default_area = next(iter(area_labels), "bar")
            selected_area = normalize_text(request.form.get("area", default_area)).lower()
            if selected_area not in area_labels:
                selected_area = default_area

            district = normalize_text(request.form.get("district", ""))
            item_names = [normalize_text(v) for v in request.form.getlist("item_names")]
            item_names = [v for v in item_names if v]
            item_names = list(dict.fromkeys(item_names))

            if not district:
                flash("Informe o nome da zona/distrito.", "error")
                return redirect(url_for("todo", area=selected_area))
            if not item_names:
                flash("Selecione pelo menos um item para a zona.", "error")
                return redirect(url_for("todo", area=selected_area))

            conn.execute(
                "DELETE FROM todo_catalog WHERE area = ? AND district = ?",
                (selected_area, district),
            )
            for idx, item_name in enumerate(item_names, start=1):
                conn.execute(
                    """
                    INSERT INTO todo_catalog (area, district, item_name, sort_order, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (selected_area, district, item_name, idx),
                )

        flash("Zona do checklist guardada.", "ok")
        return redirect(url_for("todo", area=selected_area))

    @app.route("/todo/catalog/delete", methods=["POST"])
    def todo_catalog_delete():
        if (redir := login_required()) is not None:
            return redir
        if (redir := manager_required()) is not None:
            return redir

        with get_db(app) as conn:
            area_labels = get_todo_area_labels(conn)
            default_area = next(iter(area_labels), "bar")
            selected_area = normalize_text(request.form.get("area", default_area)).lower()
            if selected_area not in area_labels:
                selected_area = default_area
            district = normalize_text(request.form.get("district", ""))
            if not district:
                flash("Zona invalida.", "error")
                return redirect(url_for("todo", area=selected_area))

            conn.execute(
                "DELETE FROM todo_catalog WHERE area = ? AND district = ?",
                (selected_area, district),
            )

        flash("Zona removida do checklist.", "ok")
        return redirect(url_for("todo", area=selected_area))

    @app.route("/todo", methods=["GET", "POST"])
    def todo():
        if (redir := login_required()) is not None:
            return redir

        with get_db(app) as conn:
            area_labels = get_todo_area_labels(conn)
        default_area = next(iter(area_labels), "bar")
        selected_area = normalize_text(request.args.get("area", default_area)).lower()
        today_iso = now_iso()
        selected_date = normalize_text(request.args.get("date", today_iso))
        edit_mode = request.args.get("edit", "") == "1"
        if selected_area not in area_labels:
            selected_area = default_area
        try:
            datetime.strptime(selected_date, "%Y-%m-%d")
        except ValueError:
            selected_date = today_iso
        is_today = selected_date == today_iso
        if not is_today:
            edit_mode = False

        if request.method == "POST":
            selected_area = normalize_text(request.form.get("area", selected_area)).lower()
            if selected_area not in area_labels:
                selected_area = default_area

            raw_missing = (request.form.get("missing_items") or "").strip()
            parsed_missing = []
            if raw_missing:
                try:
                    parsed = json.loads(raw_missing)
                except json.JSONDecodeError:
                    parsed = []
                if isinstance(parsed, list):
                    parsed_missing = parsed

            selected_pairs = set()
            for entry in parsed_missing:
                if not isinstance(entry, dict):
                    continue
                district = normalize_text(entry.get("district", ""))
                item_name = normalize_text(entry.get("item_name", ""))
                if district and item_name:
                    selected_pairs.add((district, item_name))

            with get_db(app) as conn:
                catalog_rows = conn.execute(
                    """
                    SELECT district, item_name
                    FROM todo_catalog
                    WHERE active = 1 AND area = ?
                    ORDER BY district, sort_order, item_name
                    """,
                    (selected_area,),
                ).fetchall()
                valid_pairs = {(row[0], row[1]) for row in catalog_rows}
                selected_pairs = {pair for pair in selected_pairs if pair in valid_pairs}

                check_date = now_iso()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO todo_checks (check_date, area, created_by, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (check_date, selected_area, session.get("user_id"), check_date),
                )
                check_row = conn.execute(
                    "SELECT id FROM todo_checks WHERE check_date = ? AND area = ?",
                    (check_date, selected_area),
                ).fetchone()
                check_id = check_row[0]

                conn.execute("DELETE FROM todo_check_entries WHERE check_id = ?", (check_id,))
                for district, item_name in catalog_rows:
                    conn.execute(
                        """
                        INSERT INTO todo_check_entries (check_id, district, item_name, is_missing, notes)
                        VALUES (?, ?, ?, ?, '')
                        """,
                        (check_id, district, item_name, 1 if (district, item_name) in selected_pairs else 0),
                    )

            if selected_pairs:
                return redirect(url_for("todo_order_review", area=selected_area))

            flash("Checklist diaria guardada.", "ok")
            return redirect(url_for("todo", area=selected_area, date=today_iso))

        with get_db(app) as conn:
            catalog_rows = conn.execute(
                """
                SELECT district, item_name
                FROM todo_catalog
                WHERE active = 1 AND area = ?
                ORDER BY district, sort_order, item_name
                """,
                (selected_area,),
            ).fetchall()
            available_item_rows = conn.execute(
                """
                SELECT DISTINCT name
                FROM items
                WHERE active = 1 AND TRIM(name) <> ''
                ORDER BY name
                """
            ).fetchall()

            check_row = conn.execute(
                "SELECT id FROM todo_checks WHERE check_date = ? AND area = ?",
                (selected_date, selected_area),
            ).fetchone()

            missing_pairs = set()
            report_by_district = []
            check_exists_today = bool(check_row)
            if check_row:
                rows = conn.execute(
                    """
                    SELECT district, item_name
                    FROM todo_check_entries
                    WHERE check_id = ? AND is_missing = 1
                    """,
                    (check_row[0],),
                ).fetchall()
                missing_pairs = {(row[0], row[1]) for row in rows}

                report_rows = conn.execute(
                    """
                    SELECT district, item_name, is_missing
                    FROM todo_check_entries
                    WHERE check_id = ?
                    ORDER BY district, item_name
                    """,
                    (check_row[0],),
                ).fetchall()

                grouped = {}
                for district, item_name, is_missing in report_rows:
                    grouped.setdefault(district, []).append(
                        {"item_name": item_name, "is_missing": bool(is_missing)}
                    )
                report_by_district = list(grouped.items())

            history_rows = conn.execute(
                """
                SELECT tc.check_date
                FROM todo_checks tc
                WHERE tc.area = ?
                ORDER BY tc.check_date DESC
                LIMIT 30
                """,
                (selected_area,),
            ).fetchall()

        districts = {}
        for district, item_name in catalog_rows:
            districts.setdefault(district, []).append(item_name)
        catalog_manage_map = {district: sorted(names) for district, names in districts.items()}
        available_item_names = [row[0] for row in available_item_rows]
        role = (session.get("role") or "").strip().lower()
        can_manage_todo_catalog = role in {"admin", "manager", "gestor"}

        total_items = sum(len(items) for items in districts.values())
        total_missing = len(missing_pairs)
        history_dates = []
        for row in history_rows:
            date_iso = row[0]
            try:
                display = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                display = date_iso
            history_dates.append(
                {
                    "iso": date_iso,
                    "display": display,
                    "selected": date_iso == selected_date,
                }
            )

        return render_template(
            "todo.html",
            user=current_user(),
            area_labels=area_labels,
            selected_area=selected_area,
            selected_date=selected_date,
            districts=list(districts.items()),
            missing_pairs=missing_pairs,
            total_items=total_items,
            total_missing=total_missing,
            today_iso=today_iso,
            check_exists_today=check_exists_today,
            report_by_district=report_by_district,
            edit_mode=edit_mode,
            is_today=is_today,
            history_dates=history_dates,
            can_manage_todo_catalog=can_manage_todo_catalog,
            catalog_manage_map=catalog_manage_map,
            available_item_names=available_item_names,
        )

    @app.route("/todo/order-review", methods=["GET", "POST"])
    def todo_order_review():
        if (redir := login_required()) is not None:
            return redir

        today = now_iso()
        with get_db(app) as conn:
            area_labels = get_todo_area_labels(conn)
            default_area = next(iter(area_labels), "bar")
            selected_area = normalize_text(request.args.get("area", default_area)).lower()
            if selected_area not in area_labels:
                selected_area = default_area

            check_row = conn.execute(
                "SELECT id FROM todo_checks WHERE check_date = ? AND area = ?",
                (today, selected_area),
            ).fetchone()
            if not check_row:
                flash("Ainda nao existe checklist para hoje nesta area.", "error")
                return redirect(url_for("todo", area=selected_area))

            missing_rows = conn.execute(
                """
                SELECT district, item_name
                FROM todo_check_entries
                WHERE check_id = ? AND is_missing = 1
                ORDER BY district, item_name
                """,
                (check_row[0],),
            ).fetchall()

            if not missing_rows:
                flash("Nao existem faltas para encomendar.", "ok")
                return redirect(url_for("todo", area=selected_area))

            check_id = check_row[0]
            candidate_rows = conn.execute(
                """
                SELECT
                    i.id,
                    i.name,
                    COALESCE(i.unit, ''),
                    COALESCE(s.id, 0) AS supplier_id,
                    COALESCE(s.name, 'Sem fornecedor') AS supplier_name
                FROM items i
                LEFT JOIN suppliers s ON s.id = i.supplier_id
                WHERE i.active = 1
                ORDER BY i.name, s.name
                """
            ).fetchall()
            existing_links_rows = conn.execute(
                """
                SELECT item_id, order_id, qty
                FROM todo_order_links
                WHERE check_id = ?
                """,
                (check_id,),
            ).fetchall()

        missing_lookup = {}
        for district, item_name in missing_rows:
            key = norm_key(item_name)
            missing_lookup.setdefault(key, {"item_name": item_name, "districts": set()})
            missing_lookup[key]["districts"].add(district)

        candidates_by_key = {}
        all_candidates = []
        for row in candidate_rows:
            candidate = {
                "item_id": row[0],
                "item_name": row[1],
                "unit": row[2],
                "supplier_id": row[3],
                "supplier_name": row[4],
            }
            key = norm_key(row[1])
            candidates_by_key.setdefault(key, []).append(candidate)
            all_candidates.append((key, candidate))

        existing_links = {
            row[0]: {"order_id": row[1], "qty": float(row[2] or 0)}
            for row in existing_links_rows
        }

        report_rows = []
        default_selected_ids = []
        for key, info in missing_lookup.items():
            candidates = candidates_by_key.get(key, [])
            best = candidates[0] if candidates else None

            if not best:
                fuzzy_matches = []
                for item_key, candidate in all_candidates:
                    if key in item_key or item_key in key:
                        fuzzy_matches.append(candidate)
                if fuzzy_matches:
                    fuzzy_matches.sort(key=lambda c: len(normalize_text(c["item_name"])))
                    best = fuzzy_matches[0]

            row = {
                "item_name": info["item_name"],
                "districts": sorted(info["districts"]),
                "candidate": best,
                "has_candidate": bool(best),
                "already_ordered": bool(best and best["item_id"] in existing_links),
            }
            report_rows.append(row)
            if best:
                default_selected_ids.append(str(best["item_id"]))

        if request.method == "POST":
            action = (request.form.get("action") or "").strip().lower()
            selected_ids = request.form.getlist("selected_item_ids")
            selected_ids_int = []
            for raw in selected_ids:
                try:
                    selected_ids_int.append(int(raw))
                except ValueError:
                    continue
            selected_ids_int = list(dict.fromkeys(selected_ids_int))

            desired_ids = set(selected_ids_int) if action != "skip" else set()
            existing_ids = set(existing_links.keys())
            to_add_ids = sorted(desired_ids - existing_ids)
            to_remove_ids = sorted(existing_ids - desired_ids)

            if action != "skip" and not desired_ids and not existing_ids:
                flash("Nenhum item selecionado para encomenda.", "error")
                return redirect(url_for("todo_order_review", area=selected_area))

            ordered_at = now_iso()
            added_count = 0
            removed_count = 0

            with get_db(app) as conn:
                # Remove previously ordered items that are no longer selected.
                for item_id in to_remove_ids:
                    link = existing_links.get(item_id)
                    if not link:
                        continue
                    order_id = int(link["order_id"])
                    qty_to_remove = float(link["qty"])

                    order_row = conn.execute(
                        """
                        SELECT id, item_id, qty, status
                        FROM orders
                        WHERE id = ?
                        """,
                        (order_id,),
                    ).fetchone()
                    if not order_row:
                        conn.execute(
                            "DELETE FROM todo_order_links WHERE check_id = ? AND item_id = ?",
                            (check_id, item_id),
                        )
                        continue

                    current_qty = float(order_row[2] or 0)
                    new_qty = current_qty - qty_to_remove
                    if new_qty <= 0:
                        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
                        conn.execute("DELETE FROM market_list WHERE order_id = ?", (order_id,))
                    else:
                        conn.execute("UPDATE orders SET qty = ? WHERE id = ?", (new_qty, order_id))
                        market_row = conn.execute(
                            """
                            SELECT id, COALESCE(unit, '')
                            FROM market_list
                            WHERE order_id = ?
                            LIMIT 1
                            """,
                            (order_id,),
                        ).fetchone()
                        if market_row:
                            unit = normalize_text(market_row[1])
                            qty_text = f"{new_qty:.2f}".rstrip("0").rstrip(".")
                            if unit:
                                qty_text = f"{qty_text} {unit}"
                            conn.execute(
                                """
                                UPDATE market_list
                                SET qty_value = ?, qty = ?
                                WHERE id = ?
                                """,
                                (new_qty, qty_text, market_row[0]),
                            )

                    conn.execute(
                        "DELETE FROM todo_order_links WHERE check_id = ? AND item_id = ?",
                        (check_id, item_id),
                    )
                    removed_count += 1

                # Add new selected items that were not ordered yet for this checklist.
                if to_add_ids:
                    placeholders = ", ".join("?" for _ in to_add_ids)
                    item_rows = conn.execute(
                        f"""
                        SELECT
                            i.id,
                            i.supplier_id,
                            i.name,
                            COALESCE(s.name, ''),
                            COALESCE(i.unit, '')
                        FROM items i
                        LEFT JOIN suppliers s ON s.id = i.supplier_id
                        WHERE i.id IN ({placeholders})
                        """,
                        tuple(to_add_ids),
                    ).fetchall()
                    item_lookup = {row[0]: row for row in item_rows}

                    for item_id in to_add_ids:
                        item_row = item_lookup.get(item_id)
                        if not item_row:
                            continue

                        qty = 1.0
                        supplier_id = item_row[1]
                        item_name = item_row[2]
                        supplier_name = normalize_text(item_row[3]).lower()
                        item_unit = normalize_text(item_row[4])
                        is_market_supplier = supplier_name == "mercado"
                        order_id = None

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
                        else:
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
                                order_id = pending_row[0]
                                conn.execute(
                                    """
                                    UPDATE orders
                                    SET qty = qty + ?, ordered_at = ?
                                    WHERE id = ?
                                    """,
                                    (qty, ordered_at, order_id),
                                )
                            else:
                                cur = conn.execute(
                                    """
                                    INSERT INTO orders (supplier_id, item_id, qty, status, total, ordered_at)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (supplier_id, item_id, qty, "pending", 0, ordered_at),
                                )
                                order_id = cur.lastrowid

                        if order_id:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO todo_order_links (check_id, item_id, order_id, qty, created_at)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (check_id, item_id, order_id, qty, ordered_at),
                            )
                            added_count += 1

            if action == "skip":
                if removed_count:
                    flash("Checklist atualizada e encomendas removidas.", "ok")
                else:
                    flash("Checklist guardada sem encomenda.", "ok")
                return redirect(url_for("todo", area=selected_area))

            if added_count == 0 and removed_count == 0:
                flash("Sem alteracoes de encomenda.", "ok")
            else:
                parts = []
                if added_count:
                    parts.append(f"{added_count} adicionado(s)")
                if removed_count:
                    parts.append(f"{removed_count} removido(s)")
                flash("Encomenda atualizada: " + " · ".join(parts) + ".", "ok")
            return redirect(url_for("orders"))

        return render_template(
            "todo_order_review.html",
            user=current_user(),
            area_labels=area_labels,
            selected_area=selected_area,
            today_iso=today,
            report_rows=report_rows,
            default_selected_ids=default_selected_ids,
            ordered_item_ids={str(item_id) for item_id in existing_links.keys()},
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

    @app.route("/orders/<int:order_id>/qty", methods=["POST"])
    def orders_update_qty(order_id):
        if (redir := login_required()) is not None:
            return redir

        payload = request.get_json(silent=True) or {}
        try:
            qty = float(payload.get("qty", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Quantidade invalida."}), 400
        if qty <= 0:
            return jsonify({"ok": False, "error": "Quantidade invalida."}), 400

        with get_db(app) as conn:
            row = conn.execute(
                "SELECT id, item_id, status FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            if not row or row[2] != "pending":
                return jsonify({"ok": False, "error": "Item pendente nao encontrado."}), 404

            conn.execute(
                "UPDATE orders SET qty = ? WHERE id = ?",
                (qty, order_id),
            )
            item_meta = conn.execute(
                "SELECT COALESCE(unit, '') FROM items WHERE id = ?",
                (row[1],),
            ).fetchone()
            unit = normalize_text(item_meta[0] if item_meta else "")
            qty_text = f"{qty:.2f}".rstrip("0").rstrip(".")
            if unit:
                qty_text = f"{qty_text} {unit}"
            conn.execute(
                """
                UPDATE market_list
                SET qty = ?, qty_value = ?
                WHERE order_id = ? AND checked = 0
                """,
                (qty_text, qty, order_id),
            )
        return jsonify({"ok": True, "qty": qty})

    @app.route("/orders/<int:order_id>/remove", methods=["POST"])
    def orders_remove(order_id):
        if (redir := login_required()) is not None:
            return redir

        with get_db(app) as conn:
            row = conn.execute(
                "SELECT id, status FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            if not row or row[1] != "pending":
                return jsonify({"ok": False, "error": "Item pendente nao encontrado."}), 404

            conn.execute("DELETE FROM market_list WHERE order_id = ?", (order_id,))
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))

        return jsonify({"ok": True})

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
