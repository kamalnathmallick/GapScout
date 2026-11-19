"""Integration tests for the schema and migrations.

These run against a real PostGIS database. A throwaway ``<database>_test``
database is created, migrated to head, exercised, then downgraded and dropped.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from geoalchemy2.elements import WKTElement
from sqlalchemy import Engine, create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.models import (
    DoNotContact,
    Lead,
    ModelVersion,
    Place,
    SearchJob,
    SearchJobCell,
    Workspace,
)

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


def _new_workspace(engine: Engine, name: str = "Test workspace") -> uuid.UUID:
    with engine.begin() as connection:
        workspace_id = connection.execute(
            text("INSERT INTO workspaces (name) VALUES (:name) RETURNING id"), {"name": name}
        ).scalar_one()
    return workspace_id


def _new_place(engine: Engine, workspace_id: uuid.UUID, provider_place_id: str) -> uuid.UUID:
    with engine.begin() as connection:
        return connection.execute(
            text(
                """
                INSERT INTO places (workspace_id, provider, provider_place_id, name, location)
                VALUES (
                    :workspace_id, 'seed', :provider_place_id, 'Place',
                    ST_GeogFromText('SRID=4326;POINT(77.6408 12.9784)')
                )
                RETURNING id
                """
            ),
            {"workspace_id": workspace_id, "provider_place_id": provider_place_id},
        ).scalar_one()


def test_migration_creates_expected_tables(db_engine: Engine) -> None:
    tables = set(inspect(db_engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)


def test_database_is_at_head(db_engine: Engine, alembic_config: Config) -> None:
    head = ScriptDirectory.from_config(alembic_config).get_current_head()
    with db_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == head
        )


def test_places_are_unique_per_workspace_and_provider(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    _new_place(db_engine, workspace_id, "same-id")

    with pytest.raises(IntegrityError):
        _new_place(db_engine, workspace_id, "same-id")

    # The same provider id in a different workspace is a different business.
    other_workspace_id = _new_workspace(db_engine, "Other workspace")
    _new_place(db_engine, other_workspace_id, "same-id")


def test_lead_status_check_rejects_unknown_values(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    place_id = _new_place(db_engine, workspace_id, "lead-place")

    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            Lead.__table__.insert().values(
                workspace_id=workspace_id, place_id=place_id, status="not-a-status"
            )
        )


def test_one_lead_per_place_per_workspace(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    place_id = _new_place(db_engine, workspace_id, "duplicate-lead")

    with db_engine.begin() as connection:
        connection.execute(
            Lead.__table__.insert().values(workspace_id=workspace_id, place_id=place_id)
        )

    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            Lead.__table__.insert().values(workspace_id=workspace_id, place_id=place_id)
        )


def test_spatial_query_finds_only_places_within_one_km(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    with db_engine.begin() as connection:
        connection.execute(
            Place.__table__.insert(),
            [
                {
                    "workspace_id": workspace_id,
                    "provider": "seed",
                    "provider_place_id": "near",
                    "name": "Near",
                    "location": WKTElement("POINT(77.6408 12.9784)", srid=4326),
                },
                {
                    "workspace_id": workspace_id,
                    "provider": "seed",
                    "provider_place_id": "far",
                    "name": "Far",
                    # ~2.2 km north
                    "location": WKTElement("POINT(77.6408 12.9984)", srid=4326),
                },
            ],
        )

    with db_engine.connect() as connection:
        nearby = connection.execute(
            select(func.count())
            .select_from(Place.__table__)
            .where(
                Place.__table__.c.workspace_id == workspace_id,
                func.ST_DWithin(
                    Place.__table__.c.location,
                    func.ST_GeogFromText("SRID=4326;POINT(77.6408 12.9784)"),
                    1000,
                ),
            )
        ).scalar_one()

    assert nearby == 1


def test_only_one_active_model_version_per_workspace(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    with db_engine.begin() as connection:
        connection.execute(
            ModelVersion.__table__.insert().values(
                workspace_id=workspace_id, algorithm="logistic_regression", is_active=True
            )
        )

    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            ModelVersion.__table__.insert().values(
                workspace_id=workspace_id, algorithm="lightgbm", is_active=True
            )
        )


def test_do_not_contact_needs_at_least_one_identifier(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(DoNotContact.__table__.insert().values(workspace_id=workspace_id))

    with db_engine.begin() as connection:
        connection.execute(
            DoNotContact.__table__.insert().values(
                workspace_id=workspace_id, email="owner@example.com"
            )
        )

    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            DoNotContact.__table__.insert().values(
                workspace_id=workspace_id, email="owner@example.com"
            )
        )


def test_every_user_data_table_carries_workspace_id(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    user_data_tables = [
        "users",
        "search_jobs",
        "places",
        "place_reviews",
        "hex_metrics",
        "leads",
        "lead_features",
        "enrichments",
        "outreach_drafts",
        "outreach_events",
        "model_versions",
        "do_not_contact",
    ]

    for table in user_data_tables:
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        assert "workspace_id" in columns, f"{table} is missing workspace_id"
        assert columns["workspace_id"]["nullable"] is False, f"{table}.workspace_id is nullable"


def test_lead_and_place_rows_carry_workspace_id(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    place_id = _new_place(db_engine, workspace_id, "tenancy-place")
    with db_engine.begin() as connection:
        connection.execute(
            Lead.__table__.insert().values(workspace_id=workspace_id, place_id=place_id)
        )

    assert Lead.__table__.c.workspace_id.nullable is False
    assert Place.__table__.c.workspace_id.nullable is False
    assert Workspace.__table__.c.name.nullable is False


def test_search_job_cells_constraints_and_cascade(db_engine: Engine) -> None:
    workspace_id = _new_workspace(db_engine)
    with db_engine.begin() as connection:
        job_id = connection.execute(
            SearchJob.__table__.insert()
            .values(workspace_id=workspace_id, category="cafe")
            .returning(SearchJob.id)
        ).scalar_one()

        polygon_wkt = (
            "SRID=4326;POLYGON((77.63 12.96, 77.65 12.96, 77.65 12.98, 77.63 12.98, 77.63 12.96))"
        )
        connection.execute(
            SearchJobCell.__table__.insert().values(
                search_job_id=job_id,
                cell_index=0,
                bbox=func.ST_GeomFromEWKT(polygon_wkt),
                status="pending",
            )
        )

    # Unique constraint on (search_job_id, cell_index)
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            SearchJobCell.__table__.insert().values(
                search_job_id=job_id,
                cell_index=0,
                bbox=func.ST_GeomFromEWKT(polygon_wkt),
                status="pending",
            )
        )

    # Status CHECK constraint rejects unknown values
    with pytest.raises(IntegrityError), db_engine.begin() as connection:
        connection.execute(
            SearchJobCell.__table__.insert().values(
                search_job_id=job_id,
                cell_index=1,
                bbox=func.ST_GeomFromEWKT(polygon_wkt),
                status="invalid_status",
            )
        )

    # Deleting search job cascades to search_job_cells
    with db_engine.begin() as connection:
        connection.execute(SearchJob.__table__.delete().where(SearchJob.id == job_id))
        count = connection.execute(
            select(func.count())
            .select_from(SearchJobCell)
            .where(SearchJobCell.search_job_id == job_id)
        ).scalar_one()
        assert count == 0
