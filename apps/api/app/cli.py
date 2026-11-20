"""GapScout CLI commands."""

import argparse
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Workspace
from app.providers.gosom import GosomScraperProvider
from app.services.places import upsert_places


def get_or_create_default_workspace(session: Session) -> uuid.UUID:
    """Return the ID of an existing workspace or create a default demo workspace."""
    workspace = session.execute(select(Workspace).limit(1)).scalar_one_or_none()
    if workspace:
        return workspace.id

    new_ws = Workspace(name="Default Workspace")
    session.add(new_ws)
    session.commit()
    session.refresh(new_ws)
    return new_ws.id


def run_scrape(
    category: str,
    area: str,
    workspace_id_str: str | None = None,
    depth: int = 1,
    max_time: int = 300,
) -> int:
    """Execute a scrape via GosomScraperProvider and upsert results into the database."""
    settings = get_settings()
    provider = GosomScraperProvider(base_url=settings.scraper_base_url)

    print(f"Scraping category '{category}' in area '{area}' via {provider.name}...")

    with SessionLocal() as session:
        if workspace_id_str:
            workspace_id = uuid.UUID(workspace_id_str)
        else:
            workspace_id = get_or_create_default_workspace(session)

        from app.providers.base import SearchOptions

        options = SearchOptions(depth=depth, max_time=max_time)
        dtos = provider.search_and_map(category=category, area_or_cell=area, options=options)

        print(f"Found {len(dtos)} places from upstream scraper. Upserting into database...")
        place_ids = upsert_places(session, workspace_id, dtos)
        print(f"Successfully upserted {len(place_ids)} places into workspace {workspace_id}.")
        return len(place_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="GapScout CLI tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape", help="Run a scrape query and store the results in the database"
    )
    scrape_parser.add_argument("--category", required=True, help="Business category (e.g. 'cafes')")
    scrape_parser.add_argument(
        "--area", required=True, help="Geographic area (e.g. 'Indiranagar, Bangalore')"
    )
    scrape_parser.add_argument(
        "--workspace-id", dest="workspace_id", default=None, help="Workspace UUID"
    )
    scrape_parser.add_argument(
        "--depth", type=int, default=1, help="Search scroll depth (default: 1)"
    )
    scrape_parser.add_argument(
        "--max-time", type=int, default=300, help="Maximum job execution time in seconds"
    )

    args = parser.parse_args()

    if args.command == "scrape":
        count = run_scrape(
            category=args.category,
            area=args.area,
            workspace_id_str=args.workspace_id,
            depth=args.depth,
            max_time=args.max_time,
        )
        print(f"Done. Processed {count} places.")


if __name__ == "__main__":
    main()
