from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from exposibot.extensions import db


def _now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)

    sermons = db.relationship(
        "Sermon", backref="author", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Sermon(db.Model):
    __tablename__ = "sermons"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    reference = db.Column(db.String(255), default="")
    title = db.Column(db.String(255), default="")
    status = db.Column(db.String(20), default="research")  # research | outline | final

    # Lista de {"tipo": str, "markdown": str} - guardamos o markdown de origem,
    # nunca HTML bruto, para renderizar com segurança na leitura.
    research_notes = db.Column(db.JSON, default=list)

    # {ict, tese, proposito_basico, proposito_especifico, intro, topicos: [...], conclusao}
    outline = db.Column(db.JSON, default=dict)

    # {"version": str, "text": str} - cache do texto bíblico já buscado
    passage_cache = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    def display_title(self):
        return self.title or self.reference or "Sermão sem título"
