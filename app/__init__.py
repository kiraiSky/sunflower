from flask import Flask

from .models import init_db
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["DATABASE"] = "data.db"

    init_db(app)
    register_routes(app)
    return app
