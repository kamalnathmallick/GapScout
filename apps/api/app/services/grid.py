"""Grid planner: divides bounding boxes into overlapping search cells with runtime estimates."""

import math

from pydantic import BaseModel

from app.config import get_settings
from app.services.geocoding import BoundingBox

METERS_PER_LAT_DEGREE = 111320.0


class GridCell(BaseModel):
    """A single grid search cell."""

    index: int
    center_lat: float
    center_lon: float
    radius_m: float
    bbox: BoundingBox


class GridPlan(BaseModel):
    """The computed grid plan for a search job."""

    area_bbox: BoundingBox
    cell_size_m: float
    overlap_ratio: float
    cells: list[GridCell]
    estimated_seconds: float
    estimated_cost_usd: float

    @property
    def total_cells(self) -> int:
        return len(self.cells)


class GridCapExceededError(ValueError):
    """Raised when generated cells exceed the allowed safety cap."""


def meters_to_lat_degrees(meters: float) -> float:
    return meters / METERS_PER_LAT_DEGREE


def meters_to_lon_degrees(meters: float, latitude: float) -> float:
    cos_lat = math.cos(math.radians(latitude))
    # Guard against extreme polar latitudes
    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6
    return meters / (METERS_PER_LAT_DEGREE * cos_lat)


def generate_grid_plan(
    bbox: BoundingBox,
    cell_size_m: float = 1000.0,
    overlap_ratio: float = 0.15,
    concurrency: int | None = None,
    max_cells: int | None = None,
    avg_cell_seconds: float = 12.0,
) -> GridPlan:
    """Divide a bounding box into overlapping search cells.

    Ensures full coverage of the bounding box while maintaining a controlled overlap
    and enforcing workspace safety caps.
    """
    settings = get_settings()
    cap = max_cells or settings.max_cells_per_job
    conc = concurrency or settings.scraper_concurrency

    mid_lat = bbox.center_lat
    step_m = cell_size_m * (1.0 - overlap_ratio)

    lat_step_deg = meters_to_lat_degrees(step_m)
    lon_step_deg = meters_to_lon_degrees(step_m, mid_lat)

    cell_half_lat = meters_to_lat_degrees(cell_size_m / 2.0)
    cell_half_lon = meters_to_lon_degrees(cell_size_m / 2.0, mid_lat)

    lat_span = bbox.max_lat - bbox.min_lat
    lon_span = bbox.max_lon - bbox.min_lon

    n_lat = max(1, math.ceil(lat_span / lat_step_deg))
    n_lon = max(1, math.ceil(lon_span / lon_step_deg))

    total_cells = n_lat * n_lon
    if total_cells > cap:
        raise GridCapExceededError(
            f"Grid generated {total_cells} cells ({n_lat}x{n_lon}), "
            f"exceeding the safety cap of {cap} cells per job."
        )

    # Search radius to fully enclose cell: sqrt((w/2)^2 + (h/2)^2)
    radius_m = (cell_size_m / 2.0) * math.sqrt(2)

    cells: list[GridCell] = []
    idx = 0

    # Distribute centers evenly over the span
    for i in range(n_lat):
        if n_lat == 1:
            c_lat = bbox.center_lat
        else:
            step_lat = (lat_span - 2 * cell_half_lat) / max(1, n_lat - 1)
            c_lat = bbox.min_lat + cell_half_lat + i * step_lat

        for j in range(n_lon):
            if n_lon == 1:
                c_lon = bbox.center_lon
            else:
                step_lon = (lon_span - 2 * cell_half_lon) / max(1, n_lon - 1)
                c_lon = bbox.min_lon + cell_half_lon + j * step_lon

            cell_bbox = BoundingBox(
                min_lat=c_lat - cell_half_lat,
                max_lat=c_lat + cell_half_lat,
                min_lon=c_lon - cell_half_lon,
                max_lon=c_lon + cell_half_lon,
            )

            cells.append(
                GridCell(
                    index=idx,
                    center_lat=c_lat,
                    center_lon=c_lon,
                    radius_m=radius_m,
                    bbox=cell_bbox,
                )
            )
            idx += 1

    estimated_seconds = math.ceil((len(cells) / max(1, conc)) * avg_cell_seconds)
    # The default gosom scraper runs locally with zero API cost
    estimated_cost_usd = 0.0

    return GridPlan(
        area_bbox=bbox,
        cell_size_m=cell_size_m,
        overlap_ratio=overlap_ratio,
        cells=cells,
        estimated_seconds=float(estimated_seconds),
        estimated_cost_usd=estimated_cost_usd,
    )
