"""Gap analysis schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HexMetricOut(BaseModel):
    """Hexagon metrics and opportunity score."""

    id: uuid.UUID
    search_job_id: uuid.UUID
    category: str
    h3_index: str
    resolution: int
    supply_count: int
    density_per_km2: float | None
    avg_rating: float | None
    avg_review_count: float | None
    demand_proxy: float | None
    opportunity_score: float | None
    label: str | None
    explanation: dict[str, Any]
    computed_at: datetime

    model_config = {"from_attributes": True}


class HexFeatureGeoJSON(BaseModel):
    """GeoJSON Feature representation of a hex metric."""

    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class HexCollectionGeoJSON(BaseModel):
    """GeoJSON FeatureCollection of hex metrics."""

    type: str = "FeatureCollection"
    features: list[HexFeatureGeoJSON]


class HexMetricsResponse(BaseModel):
    """Response containing list of hex metrics and GeoJSON format."""

    job_id: uuid.UUID
    category: str
    resolution: int
    hexes: list[HexMetricOut]
    geojson: HexCollectionGeoJSON


class GapSummaryOut(BaseModel):
    """Overall area gap analysis summary."""

    job_id: uuid.UUID
    category: str
    resolution: int
    total_hexes: int
    underserved_count: int
    balanced_count: int
    oversaturated_count: int
    insufficient_data_count: int
    area_median_rating: float
    best_hexes: list[dict[str, Any]]
    saturated_hexes: list[dict[str, Any]]
