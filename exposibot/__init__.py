import hmac
import os
import secrets

import markdown as md
from dotenv import load_dotenv
from flask import Flask, abort, request, session
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
    """Obtém a SECRET_KEY sem recorrer a um valor público e previsível."""
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


def _csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(test_config=None):
    """Cria a aplicação Flask.

    ``test_config`` permite substituir configurações em testes sem alterar o
    comportamento de produção. Em produção, ``create_app()`` continua idêntico
    ao uso anterior.
    """
    _load_environment()

    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )

    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        SECRET_KEY=_load_or_create_secret_key(app.instance_path),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "exposibot.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)

    # Escapa HTML antes de converter Markdown para impedir que texto vindo da IA
    # ou salvo pelo usuário seja promovido a HTML executável no navegador.
    app.jinja_env.filters["markdown"] = lambda text: Markup(md.markdown(str(escape(text or ""))))
    app.jinja_env.globals["csrf_token"] = _csrf_token

    @app.before_request
    def protect_form_posts():
        # Formulários tradicionais recebem token explícito. Os endpoints /api
        # recebem JSON e não são acionáveis por formulários HTML comuns.
        if request.method == "POST" and request.blueprint != "api":
            expected = session.get("_csrf_token")
            supplied = request.form.get("csrf_token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                abort(400, description="Token CSRF ausente ou inválido.")

    from exposibot import auth, routes_api, routes_dashboard

    app.register_blueprint(auth.bp)
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_api.bp)

    with app.app_context():
        db.create_all()

    return app
