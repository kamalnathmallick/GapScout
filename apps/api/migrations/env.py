"""Alembic environment. The database URL always comes from settings."""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tests inject their own URL through config.attributes; everything else uses
# the environment. Escape % so ConfigParser interpolation does not eat it.
database_url = config.attributes.get("sqlalchemy_url") or get_settings().database_url
if hasattr(database_url, "render_as_string"):
    # str(URL) masks the password as ***; migrations need the real one.
    database_url = database_url.render_as_string(hide_password=False)
config.set_main_option("sqlalchemy.url", str(database_url).replace("%", "%%"))

target_metadata = Base.metadata


def _extension_tables(connection: Any) -> set[str]:
    """Tables owned by extensions (PostGIS, tiger geocoder, topology).

    Autogenerate must never propose dropping them, so they are excluded from
    the comparison in both directions.
    """
    rows = connection.execute(
        text(
            """
            SELECT DISTINCT c.relname
            FROM pg_class c
            JOIN pg_depend d ON d.objid = c.oid AND d.deptype = 'e'
            JOIN pg_extension e ON e.oid = d.refobjid
            """
        )
    )
    return {row[0] for row in rows}


def _include_object_factory(extension_tables: set[str]):
    def include_object(obj: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
        if not reflected:
            return True
        if type_ == "table":
            return name not in extension_tables
        if type_ in {
            "index",
            "column",
            "unique_constraint",
            "foreign_key_constraint",
            "check_constraint",
        }:
            table = getattr(obj, "table", None)
            if table is not None and table.name in extension_tables:
                return False
        return True

    return include_object


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        extension_tables = _extension_tables(connection)
        # The query above autobegins a transaction. Close it so Alembic owns the
        # migration transaction and can commit the DDL when it finishes.
        connection.rollback()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=_include_object_factory(extension_tables),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
