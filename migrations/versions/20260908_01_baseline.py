"""Baseline Exposibot schema.

Revision ID: 20260908_01
Revises:
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "20260908_01"
down_revision = None
branch_labels = None
depends_on = None


def _index_names(inspector, table_name):
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sermons" not in tables:
        op.create_table(
            "sermons",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("reference", sa.String(length=255), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("research_notes", sa.JSON(), nullable=True),
            sa.Column("outline", sa.JSON(), nullable=True),
            sa.Column("passage_cache", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sermons_user_id", "sermons", ["user_id"], unique=False)

    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names() and "ix_users_email" not in _index_names(inspector, "users"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    inspector = sa.inspect(bind)
    if "sermons" in inspector.get_table_names() and "ix_sermons_user_id" not in _index_names(inspector, "sermons"):
        op.create_index("ix_sermons_user_id", "sermons", ["user_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sermons" in tables:
        op.drop_table("sermons")
    if "users" in tables:
        op.drop_table("users")
