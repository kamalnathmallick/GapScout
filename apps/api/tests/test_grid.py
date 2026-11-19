"""Tests for grid planning: mathematical coverage, overlap, and bounds enforcement."""

import pytest

from app.services.geocoding import BoundingBox
from app.services.grid import (
    GridCapExceededError,
    generate_grid_plan,
    meters_to_lat_degrees,
    meters_to_lon_degrees,
)


def _make_3km_box() -> BoundingBox:
    # 3 km centered at Bangalore coordinates (~12.9716, 77.5946)
    # 3000m / 2 = 1500m half-extent
    center_lat = 12.9716
    center_lon = 77.5946
    d_lat = meters_to_lat_degrees(1500)
    d_lon = meters_to_lon_degrees(1500, center_lat)

    return BoundingBox(
        min_lat=center_lat - d_lat,
        max_lat=center_lat + d_lat,
        min_lon=center_lon - d_lon,
        max_lon=center_lon + d_lon,
        display_name="Test 3x3km Area",
    )


def test_grid_plan_full_coverage_and_overlap() -> None:
    area_bbox = _make_3km_box()
    cell_size_m = 1000.0  # 1 km cells
    overlap_ratio = 0.15

    plan = generate_grid_plan(area_bbox, cell_size_m=cell_size_m, overlap_ratio=overlap_ratio)

    assert plan.total_cells > 1
    # 3km / (1km * 0.85) ~ 3.5 -> 4 cells in each dimension (16 cells total)
    assert plan.total_cells == 16

    # 1. Verify coverage: min/max bounds of all cells enclose the area_bbox
    all_min_lat = min(c.bbox.min_lat for c in plan.cells)
    all_max_lat = max(c.bbox.max_lat for c in plan.cells)
    all_min_lon = min(c.bbox.min_lon for c in plan.cells)
    all_max_lon = max(c.bbox.max_lon for c in plan.cells)

    assert all_min_lat <= area_bbox.min_lat + 1e-6
    assert all_max_lat >= area_bbox.max_lat - 1e-6
    assert all_min_lon <= area_bbox.min_lon + 1e-6
    assert all_max_lon >= area_bbox.max_lon - 1e-6

    # 2. Verify all cell centers are inside the area_bbox
    for cell in plan.cells:
        assert area_bbox.min_lat <= cell.center_lat <= area_bbox.max_lat
        assert area_bbox.min_lon <= cell.center_lon <= area_bbox.max_lon

    # 3. Verify positive overlap between adjacent cells in the same row
    # Cell 0 and Cell 1 should overlap in longitude
    cell_0 = plan.cells[0]
    cell_1 = plan.cells[1]
    assert cell_0.bbox.max_lon > cell_1.bbox.min_lon, "Adjacent cells must overlap"


def test_grid_plan_runtime_and_cost_estimation() -> None:
    area_bbox = _make_3km_box()
    plan = generate_grid_plan(
        area_bbox,
        cell_size_m=1000.0,
        concurrency=2,
        avg_cell_seconds=10.0,
    )

    # 16 cells / 2 concurrency * 10 seconds = 80 seconds
    assert plan.estimated_seconds == 80.0
    assert plan.estimated_cost_usd == 0.0


def test_grid_plan_hard_caps_enforced() -> None:
    area_bbox = _make_3km_box()
    # With a small cell size of 100m, 3km requires ~35x35 = 1225 cells > 200 cap
    with pytest.raises(GridCapExceededError, match="exceeding the safety cap"):
        generate_grid_plan(area_bbox, cell_size_m=100.0, max_cells=200)
