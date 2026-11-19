"""Tests for search job orchestration: 3x3km grid, progress, pause, resume, dedupe."""

import contextlib
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Place, SearchJob, SearchJobCell, Workspace
from app.providers.base import DataSourceProvider, PlaceDTO, RawPlace, SearchOptions
from app.services.geocoding import BoundingBox
from app.services.grid import meters_to_lat_degrees, meters_to_lon_degrees
from app.services.jobs import (
    cancel_search_job,
    create_search_job,
    get_job_progress,
    pause_search_job,
    resume_search_job,
)
from app.tasks import scrape_cell_task


class FakeScraperProvider(DataSourceProvider):
    """Deterministic fake provider for test orchestration."""

    def __init__(self, fail_first_attempt: bool = False) -> None:
        self.call_count = 0
        self.fail_first_attempt = fail_first_attempt

    @property
    def name(self) -> str:
        return "fake_provider"

    def search(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[RawPlace]:
        self.call_count += 1
        opts = options or SearchOptions()
        lat = opts.lat or 12.97
        lon = opts.lon or 77.59

        # Unique place per cell location
        p1 = {
            "title": f"Local Cafe at {lat:.3f},{lon:.3f}",
            "place_id": f"place_{lat:.4f}_{lon:.4f}",
            "review_rating": "4.5",
            "review_count": "100",
            "latitude": str(lat),
            "longitude": str(lon),
        }
        # Shared overlapping place returned across multiple cells
        shared = {
            "title": "Central Hub Cafe (Overlapping)",
            "place_id": "shared_central_hub_001",
            "review_rating": "4.8",
            "review_count": "500",
            "latitude": "12.9716",
            "longitude": "77.5946",
        }

        return [
            RawPlace(provider=self.name, provider_place_id=p1["place_id"], data=p1),
            RawPlace(provider=self.name, provider_place_id=shared["place_id"], data=shared),
        ]

    def to_place_dto(self, raw: RawPlace) -> PlaceDTO:
        d = raw.data
        return PlaceDTO(
            provider=raw.provider,
            provider_place_id=raw.provider_place_id,
            name=d["title"],
            rating=float(d["review_rating"]),
            review_count=int(d["review_count"]),
            latitude=float(d["latitude"]),
            longitude=float(d["longitude"]),
            raw=d,
        )


def _make_3km_box() -> BoundingBox:
    center_lat = 12.9716
    center_lon = 77.5946
    d_lat = meters_to_lat_degrees(1500)
    d_lon = meters_to_lon_degrees(1500, center_lat)

    return BoundingBox(
        min_lat=center_lat - d_lat,
        max_lat=center_lat + d_lat,
        min_lon=center_lon - d_lon,
        max_lon=center_lon + d_lon,
        display_name="Indiranagar 3x3km",
    )


def test_orchestration_3km_box_progress_and_deduplication(db_engine) -> None:
    area_bbox = _make_3km_box()
    fake_provider = FakeScraperProvider()

    with Session(db_engine) as session:
        ws = Workspace(name="Orchestration WS")
        session.add(ws)
        session.commit()
        workspace_id = ws.id

        # 1. Create job over 3km x 3km box
        job, plan = create_search_job(
            db=session,
            workspace_id=workspace_id,
            category="cafes",
            bbox=area_bbox,
            cell_size_m=1000.0,
        )
        assert job.status == "pending"
        assert job.cells_total == 16
        assert len(plan.cells) == 16

        job_id = job.id
        cell_ids = [
            str(c.id)
            for c in session.query(SearchJobCell)
            .filter(SearchJobCell.search_job_id == job_id)
            .order_by(SearchJobCell.cell_index)
            .all()
        ]

    # 2. Execute scrape tasks for each cell with the fake provider
    with (
        patch("app.tasks.SessionLocal", return_value=Session(db_engine)),
        patch("app.tasks._get_provider", return_value=fake_provider),
        patch("app.tasks.trigger_post_scrape_pipeline.delay") as mock_pipeline_trigger,
    ):
        for i, cid in enumerate(cell_ids):
            result = scrape_cell_task(cid)
            assert result["status"] == "completed"

            # Check live progress periodically
            with Session(db_engine) as session:
                progress = get_job_progress(session, job_id)
                assert progress["cells_done"] == i + 1
                assert progress["cells_total"] == 16
                assert progress["status"] in ("running", "completed")

        # Post-scrape pipeline should be triggered once all cells complete
        mock_pipeline_trigger.assert_called_once_with(str(job_id))

    # 3. Verify final job state
    with Session(db_engine) as session:
        final_job = session.get(SearchJob, job_id)
        assert final_job.status == "completed"
        assert final_job.cells_done == 16
        assert final_job.errors_count == 0

        # Verify deduplication: 'shared_central_hub_001' returned by all 16 cells
        # but must exist only ONCE in the database places table
        shared_places = (
            session.execute(
                select(Place).where(
                    Place.workspace_id == workspace_id,
                    Place.provider_place_id == "shared_central_hub_001",
                )
            )
            .scalars()
            .all()
        )
        assert len(shared_places) == 1

        # Total places = 16 unique cell places + 1 central shared place = 17 places
        total_places = session.execute(
            select(func.count()).select_from(Place).where(Place.workspace_id == workspace_id)
        ).scalar_one()
        assert total_places == 17


def test_pause_and_resume_search_job(db_engine) -> None:
    area_bbox = _make_3km_box()

    with Session(db_engine) as session:
        ws = Workspace(name="Pause Resume WS")
        session.add(ws)
        session.commit()

        job, _ = create_search_job(
            db=session,
            workspace_id=ws.id,
            category="cafes",
            bbox=area_bbox,
            cell_size_m=1500.0,
        )
        job_id = job.id

        # Pause the job
        paused = pause_search_job(session, job_id)
        assert paused.status == "paused"

        # Resume the job
        resumed = resume_search_job(session, job_id)
        assert resumed.status == "running"


def test_cancel_search_job(db_engine) -> None:
    area_bbox = _make_3km_box()

    with Session(db_engine) as session:
        ws = Workspace(name="Cancel WS")
        session.add(ws)
        session.commit()

        job, _ = create_search_job(
            db=session,
            workspace_id=ws.id,
            category="cafes",
            bbox=area_bbox,
            cell_size_m=1500.0,
        )
        job_id = job.id

        cancelled = cancel_search_job(session, job_id)
        assert cancelled.status == "cancelled"

        # Check that child cells are marked cancelled
        pending_cells = (
            session.query(SearchJobCell)
            .filter(
                SearchJobCell.search_job_id == job_id,
                SearchJobCell.status == "pending",
            )
            .count()
        )
        assert pending_cells == 0


def test_cell_scrape_failure_records_error(db_engine) -> None:
    area_bbox = _make_3km_box()

    with Session(db_engine) as session:
        ws = Workspace(name="Failure WS")
        session.add(ws)
        session.commit()

        job, _ = create_search_job(
            db=session,
            workspace_id=ws.id,
            category="cafes",
            bbox=area_bbox,
            cell_size_m=3000.0,  # 1 cell
        )
        job_id = job.id
        cell = session.query(SearchJobCell).filter(SearchJobCell.search_job_id == job_id).first()
        assert cell is not None
        cell_id = str(cell.id)

    failing_provider = FakeScraperProvider()

    def fail_search(*args, **kwargs):
        raise RuntimeError("Simulated upstream network timeout")

    failing_provider.search = fail_search

    with (
        patch("app.tasks.SessionLocal", return_value=Session(db_engine)),
        patch("app.tasks._get_provider", return_value=failing_provider),
        contextlib.suppress(Exception),
    ):
        scrape_cell_task(cell_id)

    with Session(db_engine) as session:
        updated_cell = session.get(SearchJobCell, cell.id)
        assert updated_cell.error is not None
        assert "Simulated upstream network timeout" in updated_cell.error
