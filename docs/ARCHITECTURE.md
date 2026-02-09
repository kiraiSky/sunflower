Architecture
============

Scope
-----
Small Flask application for restaurant suppliers, orders, stock, and market list.
Data is stored in a local SQLite database.

Modules
-------
- `app/__init__.py` creates the Flask app and initializes the database.
- `app/models.py` contains the SQLite schema and helpers.
- `app/routes.py` defines routes for login and core features.
- `app/templates/` provides the UI.
- `app/static/styles.css` handles responsive layout for phone and desktop.

Next steps
----------
- Add user management UI (create, disable, role change).
- Add supplier-specific order history and export.
- Add units and stock adjustments.
- Move secrets and configuration to environment variables.
