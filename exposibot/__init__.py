import os

import markdown as md
from dotenv import load_dotenv
from flask import Flask
from markupsafe import Markup

from exposibot.extensions import db, login_manager


def _load_environment():
    # Caminho usado no PythonAnywhere (Essencial no PythonAnywhere).
    pa_env = os.path.join(os.path.expanduser("~/mysite"), ".env")
    if os.path.exists(pa_env):
        load_dotenv(pa_env)
    else:
        load_dotenv()  # fallback: .env no diretório de trabalho (dev local)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    _load_environment()

    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-insecure-change-me")

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        app.instance_path, "exposibot.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters["markdown"] = lambda text: Markup(md.markdown(text or ""))

    from exposibot import auth, routes_api, routes_dashboard

    app.register_blueprint(auth.bp)
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_api.bp)

    with app.app_context():
        db.create_all()

    return app
