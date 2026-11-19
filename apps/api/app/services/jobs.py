"""Search job management and lifecycle operations."""

import logging
import uuid
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SearchJob, SearchJobCell
from app.services.geocoding import BoundingBox, geocode_area
from app.services.grid import GridPlan, generate_grid_plan

logger = logging.getLogger(__name__)


class JobNotFoundError(Exception):
    """Raised when a search job is not found."""


class JobStateError(Exception):
    """Raised when an operation cannot be applied to the current job state."""


def create_search_job(
    db: Session,
    workspace_id: uuid.UUID,
    category: str,
    area_name: str | None = None,
    bbox: BoundingBox | None = None,
    cell_size_m: float = 1000.0,
    options: dict[str, Any] | None = None,
) -> tuple[SearchJob, GridPlan]:
    """Plan and persist a new SearchJob with its child SearchJobCells."""
    if not bbox:
        if not area_name:
            raise ValueError("Either area_name or bbox must be provided to create a search job.")
        bbox = geocode_area(area_name)

    grid_plan = generate_grid_plan(bbox=bbox, cell_size_m=cell_size_m)

    job_bbox_wkt = WKTElement(bbox.to_wkt_polygon(), srid=4326)
    job_params = {
        **(options or {}),
        "cell_size_m": cell_size_m,
        "overlap_ratio": grid_plan.overlap_ratio,
        "estimated_seconds": grid_plan.estimated_seconds,
        "estimated_cost_usd": grid_plan.estimated_cost_usd,
    }

    job = SearchJob(
        workspace_id=workspace_id,
        category=category,
        area_name=area_name or bbox.display_name,
        bbox=job_bbox_wkt,
        status="pending",
        params=job_params,
        cells_total=grid_plan.total_cells,
        cells_done=0,
        places_found=0,
        errors_count=0,
    )
    db.add(job)
    db.flush()  # Obtain job.id

    cells: list[SearchJobCell] = []
    for cell in grid_plan.cells:
        cell_wkt = WKTElement(cell.bbox.to_wkt_polygon(), srid=4326)
        cells.append(
            SearchJobCell(
                search_job_id=job.id,
                cell_index=cell.index,
                bbox=cell_wkt,
                status="pending",
                attempts=0,
            )
        )

    db.add_all(cells)
    db.commit()
    db.refresh(job)

    logger.info(
        "Created SearchJob %s with %d cells for category '%s'",
        job.id,
        grid_plan.total_cells,
        category,
    )
    return job, grid_plan


def pause_search_job(db: Session, job_id: uuid.UUID) -> SearchJob:
    """Pause an active or pending search job."""
    job = db.execute(select(SearchJob).where(SearchJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise JobNotFoundError(f"Job {job_id} not found.")

    if job.status not in ("running", "pending"):
        raise JobStateError(f"Cannot pause job in status '{job.status}'.")

    job.status = "paused"
    db.commit()
    db.refresh(job)
    logger.info("Paused SearchJob %s", job_id)
    return job


def cancel_search_job(db: Session, job_id: uuid.UUID) -> SearchJob:
    """Cancel an active, pending, or paused search job."""
    job = db.execute(select(SearchJob).where(SearchJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise JobNotFoundError(f"Job {job_id} not found.")

    if job.status in ("completed", "cancelled"):
        raise JobStateError(f"Cannot cancel job in status '{job.status}'.")

    job.status = "cancelled"
    job.finished_at = func.now()

    # Cancel remaining pending or running cells
    db.query(SearchJobCell).filter(
        SearchJobCell.search_job_id == job_id,
        SearchJobCell.status.in_(["pending", "running"]),
    ).update({"status": "cancelled"}, synchronize_session=False)

    db.commit()
    db.refresh(job)
    logger.info("Cancelled SearchJob %s", job_id)
    return job


def resume_search_job(db: Session, job_id: uuid.UUID) -> SearchJob:
    """Resume a paused search job."""
    job = db.execute(select(SearchJob).where(SearchJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise JobNotFoundError(f"Job {job_id} not found.")

    if job.status != "paused":
        raise JobStateError(f"Cannot resume job in status '{job.status}' (expected 'paused').")

    job.status = "running"
    db.commit()
    db.refresh(job)
    logger.info("Resumed SearchJob %s", job_id)
    return job


def get_job_progress(db: Session, job_id: uuid.UUID) -> dict[str, Any]:
    """Retrieve detailed progress metrics for a search job."""
    job = db.execute(select(SearchJob).where(SearchJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise JobNotFoundError(f"Job {job_id} not found.")

    # Count distinct places found for this search job if needed
    return {
        "id": str(job.id),
        "workspace_id": str(job.workspace_id),
        "category": job.category,
        "area_name": job.area_name,
        "status": job.status,
        "cells_total": job.cells_total,
        "cells_done": job.cells_done,
        "places_found": job.places_found,
        "errors_count": job.errors_count,
        "error": job.error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
