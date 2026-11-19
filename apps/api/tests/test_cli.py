"""Tests for CLI scraping command."""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.cli import run_scrape
from app.models import Place, Workspace
from app.providers.base import PlaceDTO


def test_cli_run_scrape_stores_places(db_engine) -> None:
    with Session(db_engine) as session:
        ws = Workspace(name="CLI Test Workspace")
        session.add(ws)
        session.commit()
        workspace_id = ws.id

    mock_dto = PlaceDTO(
        provider="gosom",
        provider_place_id="cli_cafe_123",
        name="CLI Test Cafe",
        category="Cafe",
        rating=4.5,
        review_count=80,
    )

    with (
        patch("app.cli.SessionLocal", return_value=Session(db_engine)),
        patch(
            "app.providers.gosom.GosomScraperProvider.search_and_map",
            return_value=[mock_dto],
        ) as mock_search,
    ):
        count = run_scrape(
            category="cafes",
            area="Indiranagar, Bangalore",
            workspace_id_str=str(workspace_id),
        )

        assert count == 1
        mock_search.assert_called_once()

    # Verify place stored in database
    with Session(db_engine) as session:
        saved = session.query(Place).filter(Place.provider_place_id == "cli_cafe_123").one()
        assert saved.name == "CLI Test Cafe"
        assert saved.workspace_id == workspace_id
