import hmac
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, abort, request, session

from exposibot.extensions import db, limiter, login_manager, migrate
from exposibot.security import render_markdown


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_environment():
    pa_env = os.path.join(os.path.expanduser("~/mysite"), ".env")
    if os.path.exists(pa_env):
        load_dotenv(pa_env)
    else:
        load_dotenv()


def _load_or_create_secret_key(instance_path):
    configured_key = os.getenv("SECRET_KEY")
    if configured_key:
        return configured_key

    if os.getenv("APP_ENV", "").lower() == "production":
        raise RuntimeError("SECRET_KEY é obrigatória quando APP_ENV=production.")

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


def create_app(test_config=None):
    _load_environment()

    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )
    os.makedirs(app.instance_path, exist_ok=True)

    is_production = os.getenv("APP_ENV", "").lower() == "production"
    app.config.update(
        SECRET_KEY=_load_or_create_secret_key(app.instance_path),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_production,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "exposibot.db"),
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)

    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.globals["csrf_token"] = _csrf_token

    @app.before_request
    def protect_mutating_requests():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        expected = session.get("_csrf_token")
        if request.is_json:
            supplied = request.headers.get("X-CSRFToken", "")
        else:
            supplied = request.form.get("csrf_token", "")

        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description="Token CSRF ausente ou inválido.")
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; "
            "frame-ancestors 'self'",
        )
        if is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    from exposibot import auth, routes_api, routes_dashboard

    app.register_blueprint(auth.bp)
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_api.bp)

    return app
