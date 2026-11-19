"""Search jobs endpoints: create, progress, cancel, resume."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import SearchJob, Workspace
from app.schemas.jobs import (
    GridEstimateOut,
    JobCreateRequest,
    JobOut,
    JobProgressOut,
)
from app.services.geocoding import BoundingBox, geocode_area
from app.services.grid import generate_grid_plan
from app.services.jobs import (
    cancel_search_job,
    create_search_job,
    resume_search_job,
)
from app.tasks import dispatch_job_cells

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut | GridEstimateOut, status_code=status.HTTP_201_CREATED)
def create_or_estimate_job(
    req: JobCreateRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut | GridEstimateOut:
    """Create a new search job or return dry-run estimation."""
    # 1. Resolve bounding box
    bbox: BoundingBox
    if req.bbox:
        bbox = BoundingBox(
            min_lat=req.bbox.min_lat,
            max_lat=req.bbox.max_lat,
            min_lon=req.bbox.min_lon,
            max_lon=req.bbox.max_lon,
            display_name=req.area_name or "Custom Bounding Box",
        )
    elif req.area_name:
        try:
            bbox = geocode_area(req.area_name)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geocoding failed for '{req.area_name}': {exc}",
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either area_name or bbox must be provided.",
        )

    # 2. Handle dry_run request
    if req.dry_run:
        plan = generate_grid_plan(bbox, cell_size_m=req.cell_size_m)
        area_km2 = len(plan.cells) * ((plan.cell_size_m / 1000.0) ** 2)
        return GridEstimateOut(
            cells_total=plan.total_cells,
            cell_size_m=plan.cell_size_m,
            area_km2=round(area_km2, 2),
            estimated_runtime_sec=int(plan.estimated_seconds),
            estimated_cost_usd=plan.estimated_cost_usd,
            area_name=req.area_name,
            bbox={
                "min_lat": bbox.min_lat,
                "max_lat": bbox.max_lat,
                "min_lon": bbox.min_lon,
                "max_lon": bbox.max_lon,
            },
        )

    # 3. Create job in database
    job, _ = create_search_job(
        db=db,
        workspace_id=workspace.id,
        category=req.category,
        bbox=bbox,
        area_name=req.area_name or bbox.display_name,
        cell_size_m=req.cell_size_m,
    )

    # 4. Dispatch Celery scrape subtasks
    dispatch_job_cells(job.id)

    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
def list_jobs(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[JobOut]:
    """List search jobs for current workspace."""
    stmt = (
        select(SearchJob)
        .where(SearchJob.workspace_id == workspace.id)
        .order_by(SearchJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = db.scalars(stmt).all()
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobProgressOut)
def get_job(
    job_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> JobProgressOut:
    """Get job progress and results for polling."""
    job = db.get(SearchJob, job_id)
    if not job or job.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    pct = round((job.cells_done / job.cells_total) * 100, 1) if job.cells_total > 0 else 0.0
    return JobProgressOut(
        job_id=job.id,
        status=job.status,
        cells_total=job.cells_total,
        cells_done=job.cells_done,
        pct_complete=pct,
        places_found=job.places_found,
        errors_count=job.errors_count,
        quality_report=job.params.get("quality_report") if isinstance(job.params, dict) else None,
        gap_summary=job.params.get("gap_summary") if isinstance(job.params, dict) else None,
    )


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(
    job_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    """Cancel a running search job."""
    job = db.get(SearchJob, job_id)
    if not job or job.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    cancelled_job = cancel_search_job(db, job_id)
    return JobOut.model_validate(cancelled_job)


@router.post("/{job_id}/resume", response_model=JobOut)
def resume_job(
    job_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> JobOut:
    """Resume a paused or failed search job."""
    job = db.get(SearchJob, job_id)
    if not job or job.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    resumed_job = resume_search_job(db, job_id)
    dispatch_job_cells(job.id)
    return JobOut.model_validate(resumed_job)
