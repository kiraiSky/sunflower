import os
from pathlib import Path

from flask import Flask

from .models import init_db
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    project_root = Path(__file__).resolve().parent.parent
    default_db_path = project_root / "data.db"
    app.config["DATABASE"] = os.environ.get("GIRASSOL_DB_PATH", str(default_db_path))

    init_db(app)
    register_routes(app)
    return app
