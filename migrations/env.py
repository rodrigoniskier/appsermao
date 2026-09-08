from __future__ import with_statement

from alembic import context
from flask import current_app
from logging.config import fileConfig

config = context.config
fileConfig(config.config_file_name)


def get_engine():
    try:
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())
target_db = current_app.extensions["migrate"].db


def get_metadata():
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


def _migrate_configure_args():
    """Return Flask-Migrate options without passing duplicate kwargs to Alembic."""
    args = dict(current_app.extensions["migrate"].configure_args or {})
    args.setdefault("compare_type", True)
    return args


def run_migrations_offline():
    configure_args = _migrate_configure_args()
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=get_metadata(),
        literal_binds=True,
        **configure_args,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    def process_revision_directives(context_, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                current_app.logger.info("Nenhuma alteração de esquema detectada.")

    configure_args = _migrate_configure_args()
    configure_args.setdefault("process_revision_directives", process_revision_directives)

    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **configure_args,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
