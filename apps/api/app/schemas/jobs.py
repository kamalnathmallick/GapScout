"""Search job request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BoundingBoxInput(BaseModel):
    """Bounding box coordinates."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class JobCreateRequest(BaseModel):
    """Create a search job or request dry-run estimation."""

    category: str = Field(min_length=2, description="Target business category")
    area_name: str | None = Field(default=None, description="City or neighborhood name")
    bbox: BoundingBoxInput | None = Field(default=None, description="Direct bounding box")
    cell_size_m: float = Field(default=1000.0, ge=300.0, le=5000.0)
    dry_run: bool = Field(
        default=False, description="If true, returns grid estimate without creating job"
    )


class GridEstimateOut(BaseModel):
    """Dry run grid estimate."""

    cells_total: int
    cell_size_m: float
    area_km2: float
    estimated_runtime_sec: int
    estimated_cost_usd: float
    area_name: str | None = None
    bbox: dict[str, float]


class JobOut(BaseModel):
    """Search job details."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    category: str
    area_name: str | None
    status: str
    cells_total: int
    cells_done: int
    places_found: int
    errors_count: int
    error: str | None
    params: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobProgressOut(BaseModel):
    """Search job progress and status polling response."""

    job_id: uuid.UUID
    status: str
    cells_total: int
    cells_done: int
    pct_complete: float
    places_found: int
    errors_count: int
    quality_report: dict[str, Any] | None = None
    gap_summary: dict[str, Any] | None = None
