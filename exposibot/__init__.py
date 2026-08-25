import os
import secrets

import markdown as md
from dotenv import load_dotenv
from flask import Flask
from markupsafe import Markup, escape

from exposibot.extensions import db, login_manager


def _load_environment():
    # Caminho usado no PythonAnywhere (Essencial no PythonAnywhere).
    pa_env = os.path.join(os.path.expanduser("~/mysite"), ".env")
    if os.path.exists(pa_env):
        load_dotenv(pa_env)
    else:
        load_dotenv()  # fallback: .env no diretório de trabalho (dev local)


def _load_or_create_secret_key(instance_path):
    """Obtém a SECRET_KEY sem recorrer a um valor público e previsível.

    A variável de ambiente continua sendo a opção preferida. Se ela não estiver
    definida, gera uma chave persistente dentro da pasta instance, que não faz
    parte do repositório e permanece estável entre reinícios do processo.
    """
    configured_key = os.getenv("SECRET_KEY")
    if configured_key:
        return configured_key

    os.makedirs(instance_path, exist_ok=True)
    key_path = os.path.join(instance_path, ".secret_key")

    try:
        with open(key_path, "r", encoding="utf-8") as key_file:
            existing_key = key_file.read().strip()
            if existing_key:
                return existing_key
    except FileNotFoundError:
        pass

    generated_key = secrets.token_urlsafe(48)
    with open(key_path, "w", encoding="utf-8") as key_file:
        key_file.write(generated_key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass

    return generated_key


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    _load_environment()

    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SECRET_KEY"] = _load_or_create_secret_key(app.instance_path)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        app.instance_path, "exposibot.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    # Escapa HTML antes de converter Markdown para impedir que texto vindo da IA
    # ou salvo pelo usuário seja promovido a HTML executável no navegador.
    app.jinja_env.filters["markdown"] = lambda text: Markup(md.markdown(str(escape(text or ""))))

    from exposibot import auth, routes_api, routes_dashboard

    app.register_blueprint(auth.bp)
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_api.bp)

    with app.app_context():
        db.create_all()

    return app
