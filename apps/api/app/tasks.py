"""Celery tasks for grid scrape orchestration, cell processing, and retries."""

import logging
import time
import uuid

from sqlalchemy import func, select

from app.celery_app import celery_app
from app.config import get_settings
from app.db import SessionLocal
from app.models import SearchJob, SearchJobCell
from app.providers.base import DataSourceProvider, SearchOptions
from app.providers.gosom import GosomScraperProvider
from app.services.places import upsert_places

logger = logging.getLogger(__name__)


@celery_app.task(name="gapscout.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="gapscout.clean_and_normalize_places_task")
def clean_and_normalize_places_task(job_id_str: str) -> dict:
    """Run data cleaning, normalization, duplicate detection, and quality report for a job."""
    from app.cleaning.pipeline import clean_and_normalize_job_places

    job_id = uuid.UUID(job_id_str)
    with SessionLocal() as session:
        report = clean_and_normalize_job_places(session, job_id)
        return report


@celery_app.task(name="gapscout.trigger_post_scrape_pipeline")
def trigger_post_scrape_pipeline(job_id: str) -> None:
    """Trigger cleaning and gap analysis pipelines after job completion."""
    logger.info(
        "Job %s completed! Automatically triggering Prompt 5 (cleaning) and Prompt 6 (gap)",
        job_id,
    )
    clean_and_normalize_places_task.delay(job_id)


def _get_provider(name: str = "gosom") -> DataSourceProvider:
    if name == "gosom":
        settings = get_settings()
        return GosomScraperProvider(base_url=settings.scraper_base_url)
    raise ValueError(f"Unknown data source provider: '{name}'")


@celery_app.task(
    name="gapscout.scrape_cell_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def scrape_cell_task(self, cell_id_str: str, provider_name: str = "gosom") -> dict:
    """Scrape places within a single grid cell."""
    cell_id = uuid.UUID(cell_id_str)
    settings = get_settings()

    with SessionLocal() as session:
        # Load cell and job
        cell = session.execute(
            select(SearchJobCell).where(SearchJobCell.id == cell_id)
        ).scalar_one_or_none()
        if not cell:
            logger.error("SearchJobCell %s not found", cell_id)
            return {"status": "error", "message": "Cell not found"}

        job = session.execute(
            select(SearchJob).where(SearchJob.id == cell.search_job_id)
        ).scalar_one_or_none()
        if not job:
            logger.error("SearchJob %s not found for cell %s", cell.search_job_id, cell_id)
            return {"status": "error", "message": "Job not found"}

        cell_index = cell.cell_index
        job_id = job.id
        workspace_id = job.workspace_id
        category = job.category
        area_name = job.area_name

        # 1. Check if job was cancelled or paused
        if job.status == "cancelled":
            cell.status = "cancelled"
            session.commit()
            logger.info("Job %s cancelled; skipping cell %s", job_id, cell_index)
            return {"status": "cancelled"}

        if job.status == "paused":
            logger.info("Job %s paused; skipping dispatch for cell %s", job_id, cell_index)
            return {"status": "paused"}

        # 2. Check places hard cap
        if job.places_found >= settings.max_places_per_job:
            logger.warning(
                "Job %s reached places hard cap (%d >= %d). Marking cell %s completed.",
                job_id,
                job.places_found,
                settings.max_places_per_job,
                cell_index,
            )
            cell.status = "completed"
            job.cells_done += 1
            session.commit()
            return {"status": "cap_reached"}

        # 3. Mark cell running
        cell.status = "running"
        cell.attempts += 1
        if job.status == "pending":
            job.status = "running"
            job.started_at = func.now()
        session.commit()

        # 4. Extract centroid coordinates using PostGIS functions
        coords = session.execute(
            select(
                func.ST_Y(func.ST_Centroid(SearchJobCell.bbox)),
                func.ST_X(func.ST_Centroid(SearchJobCell.bbox)),
            ).where(SearchJobCell.id == cell_id)
        ).one()
        center_lat, center_lon = coords[0], coords[1]

        # Cell size / radius from job params
        cell_size = float(job.params.get("cell_size_m", 1000.0))
        radius = int((cell_size / 2.0) * 1.414)

    # 5. Execute scrape outside session to avoid holding db locks during external HTTP
    try:
        provider = _get_provider(provider_name)
        options = SearchOptions(
            lat=center_lat,
            lon=center_lon,
            radius=radius,
            depth=1,
            max_time=120,
        )
        dtos = provider.search_and_map(
            category=category,
            area_or_cell=area_name or "Area",
            options=options,
        )
    except Exception as exc:
        logger.error("Scrape error in cell %s: %s", cell_id, exc)
        with SessionLocal() as session:
            c = session.get(SearchJobCell, cell_id)
            if c:
                c.error = str(exc)
                if self.request.retries >= self.max_retries:
                    c.status = "failed"
                    j = session.get(SearchJob, c.search_job_id)
                    if j:
                        j.errors_count += 1
                session.commit()

        # Retry with exponential backoff
        countdown = 5 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown) from exc

    # 6. Upsert found places and update progress
    with SessionLocal() as session:
        place_ids = upsert_places(session, workspace_id, dtos)

        c = session.get(SearchJobCell, cell_id)
        if c:
            c.status = "completed"
            c.error = None

        j = session.get(SearchJob, job_id)
        if j:
            j.cells_done += 1
            j.places_found += len(place_ids)

            # Check if all cells finished
            if (j.cells_done + j.errors_count) >= j.cells_total:
                j.status = "completed"
                j.finished_at = func.now()
                session.commit()
                trigger_post_scrape_pipeline.delay(str(j.id))
            else:
                session.commit()

    return {"status": "completed", "cell_index": cell_index, "places_found": len(place_ids)}


def dispatch_job_cells(
    job_id: uuid.UUID,
    concurrency_delay: float = 0.2,
) -> int:
    """Enqueue tasks for pending/failed cells of a search job."""
    with SessionLocal() as session:
        job = session.get(SearchJob, job_id)
        if not job:
            return 0

        job.status = "running"
        if not job.started_at:
            job.started_at = func.now()

        cells = (
            session.query(SearchJobCell)
            .filter(
                SearchJobCell.search_job_id == job_id,
                SearchJobCell.status.in_(["pending", "failed"]),
            )
            .order_by(SearchJobCell.cell_index.asc())
            .all()
        )
        cell_ids = [str(c.id) for c in cells]
        session.commit()

    # Dispatch tasks with polite spacing
    for cid in cell_ids:
        scrape_cell_task.delay(cid)
        if concurrency_delay > 0:
            time.sleep(concurrency_delay)

    return len(cell_ids)
