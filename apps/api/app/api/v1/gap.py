"""Gap analysis endpoints: hexes, GeoJSON, and area summary."""

import uuid
from typing import Annotated

import h3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import HexMetric, SearchJob, Workspace
from app.schemas.gap import (
    GapSummaryOut,
    HexCollectionGeoJSON,
    HexFeatureGeoJSON,
    HexMetricOut,
    HexMetricsResponse,
)

router = APIRouter(prefix="/gap", tags=["gap"])


def _hex_to_geojson_feature(metric: HexMetric) -> HexFeatureGeoJSON:
    boundary = h3.cell_to_boundary(metric.h3_index)
    # GeoJSON coordinates are [lon, lat] closed loop
    coords = [[float(lon), float(lat)] for lat, lon in boundary]
    if coords:
        coords.append(coords[0])

    return HexFeatureGeoJSON(
        type="Feature",
        geometry={"type": "Polygon", "coordinates": [coords]},
        properties={
            "h3_index": metric.h3_index,
            "opportunity_score": metric.opportunity_score,
            "label": metric.label,
            "supply_count": metric.supply_count,
            "density_per_km2": metric.density_per_km2,
            "avg_rating": metric.avg_rating,
            "avg_review_count": metric.avg_review_count,
            "demand_proxy": metric.demand_proxy,
            "explanation": metric.explanation,
        },
    )


@router.get("/{job_id}/hexes", response_model=HexMetricsResponse)
def get_job_gap_hexes(
    job_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> HexMetricsResponse:
    """Get calculated hex opportunity metrics and GeoJSON polygons for a job."""
    job = db.get(SearchJob, job_id)
    if not job or job.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    stmt = (
        select(HexMetric)
        .where(
            HexMetric.workspace_id == workspace.id,
            HexMetric.search_job_id == job_id,
        )
        .order_by(HexMetric.opportunity_score.desc().nullslast())
    )
    hex_metrics = list(db.scalars(stmt).all())

    hexes_out = [HexMetricOut.model_validate(m) for m in hex_metrics]
    features = [_hex_to_geojson_feature(m) for m in hex_metrics]

    return HexMetricsResponse(
        job_id=job.id,
        category=job.category,
        resolution=hex_metrics[0].resolution if hex_metrics else 8,
        hexes=hexes_out,
        geojson=HexCollectionGeoJSON(type="FeatureCollection", features=features),
    )


@router.get("/{job_id}/summary", response_model=GapSummaryOut)
def get_job_gap_summary(
    job_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> GapSummaryOut:
    """Get the area gap summary: top 3 best and top 3 saturated hexes with stats."""
    job = db.get(SearchJob, job_id)
    if not job or job.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    gap_summary = job.params.get("gap_summary") if isinstance(job.params, dict) else None
    if not gap_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gap analysis has not been computed yet for this job.",
        )

    return GapSummaryOut(
        job_id=job.id,
        category=gap_summary.get("category", job.category),
        resolution=gap_summary.get("resolution", 8),
        total_hexes=gap_summary.get("total_hexes", 0),
        underserved_count=gap_summary.get("underserved_count", 0),
        balanced_count=gap_summary.get("balanced_count", 0),
        oversaturated_count=gap_summary.get("oversaturated_count", 0),
        insufficient_data_count=gap_summary.get("insufficient_data_count", 0),
        area_median_rating=gap_summary.get("area_median_rating", 4.0),
        best_hexes=gap_summary.get("best_hexes", []),
        saturated_hexes=gap_summary.get("saturated_hexes", []),
    )
