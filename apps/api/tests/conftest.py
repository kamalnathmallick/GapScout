"""Pytest fixtures shared across test modules."""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import URL, make_url

from app.config import get_settings

API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = API_ROOT / "alembic.ini"
MIGRATIONS_DIR = API_ROOT / "migrations"

EXPECTED_TABLES = {
    "alembic_version",
    "do_not_contact",
    "enrichments",
    "hex_metrics",
    "lead_features",
    "leads",
    "model_versions",
    "outreach_drafts",
    "outreach_events",
    "place_reviews",
    "places",
    "search_job_cells",
    "search_jobs",
    "users",
    "workspaces",
}


@pytest.fixture(scope="session")
def test_db_url() -> URL:
    base = make_url(get_settings().database_url)
    database = f"{base.database or 'gapscout'}_test"
    return base.set(database=database)


@pytest.fixture(scope="session")
def admin_conninfo(test_db_url: URL) -> str:
    admin = test_db_url.set(database="postgres", drivername="postgresql")
    return admin.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def alembic_config(test_db_url: URL) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["sqlalchemy_url"] = test_db_url
    return config


@pytest.fixture(scope="session")
def db_engine(test_db_url: URL, admin_conninfo: str, alembic_config: Config) -> Iterator[Engine]:
    database = test_db_url.database
    with psycopg.connect(admin_conninfo, autocommit=True) as connection:
        connection.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        connection.execute(f'CREATE DATABASE "{database}"')

    command.upgrade(alembic_config, "head")
    engine = create_engine(test_db_url, connect_args={"connect_timeout": 3})
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")

        with create_engine(test_db_url).connect() as connection:
            remaining = set(inspect(connection).get_table_names())
        assert remaining.isdisjoint(EXPECTED_TABLES - {"alembic_version"}), (
            f"downgrade left tables behind: {remaining}"
        )

        with psycopg.connect(admin_conninfo, autocommit=True) as connection:
            connection.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
