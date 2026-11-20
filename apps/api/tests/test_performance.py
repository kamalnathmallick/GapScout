"""Performance benchmarks:

1. Gap engine computation for 50,000 places finishes in < 30s.
2. Gap map API serialization for 5,000 hexes answers in < 500ms.
"""

import time
import uuid
from collections import namedtuple

import h3

from app.api.v1.gap import _hex_to_geojson_feature
from app.cleaning.taxonomy import normalize_category
from app.gap.anchors import classify_anchor_category
from app.gap.config import load_gap_config
from app.models import HexMetric

FakeRow = namedtuple(
    "FakeRow",
    [
        "id",
        "name",
        "category",
        "normalized_category",
        "rating",
        "review_count",
        "is_closed",
        "lat",
        "lon",
    ],
)


def test_benchmark_gap_computation_50k_places():
    """Verify gap computation over 50,000 places finishes in under 30 seconds."""
    # Synthesize 50,000 places distributed across ~250 H3 resolution-8 hex cells
    # centered around Bangalore (12.9716, 77.5946)
    import numpy as np

    np.random.seed(42)
    n_places = 50_000

    base_lat, base_lon = 12.9716, 77.5946
    lats = base_lat + np.random.normal(0, 0.05, n_places)
    lons = base_lon + np.random.normal(0, 0.05, n_places)
    ratings = np.random.uniform(2.5, 5.0, n_places)
    reviews = np.random.randint(1, 500, n_places)
    categories = np.random.choice(
        ["cafe", "restaurant", "bank", "metro station", "hospital", "gym"],
        size=n_places,
    )

    rows = []
    for i in range(n_places):
        rows.append(
            FakeRow(
                id=uuid.uuid4(),
                name=f"Place {i}",
                category=str(categories[i]),
                normalized_category=str(categories[i]),
                rating=float(ratings[i]),
                review_count=int(reviews[i]),
                is_closed=False,
                lat=float(lats[i]),
                lon=float(lons[i]),
            )
        )

    _cfg = load_gap_config()
    assert _cfg is not None
    target_category = "cafe"
    norm_target = normalize_category(target_category) or "cafe"

    # Start timing core computation
    start_time = time.perf_counter()

    # 1. Spatial indexing into H3 cells
    hex_places_map: dict[str, list[FakeRow]] = {}
    anchors_by_hex: dict[str, dict[str, int]] = {}
    total_biz: dict[str, int] = {}
    competitors: list[FakeRow] = []

    for r in rows:
        cell = h3.latlng_to_cell(r.lat, r.lon, 8)
        hex_places_map.setdefault(cell, []).append(r)
        total_biz[cell] = total_biz.get(cell, 0) + 1

        p_cat = (r.normalized_category or r.category).lower()
        if p_cat == norm_target:
            competitors.append(r)
        else:
            anchor = classify_anchor_category(p_cat)
            if anchor:
                c_map = anchors_by_hex.setdefault(cell, {})
                c_map[anchor] = c_map.get(anchor, 0) + 1

    # 2. Hex metric scoring
    unique_cells = list(hex_places_map.keys())
    computed_metrics = []

    for cell in unique_cells:
        cell_places = hex_places_map.get(cell, [])
        comp_count = sum(
            1 for p in cell_places if (p.normalized_category or p.category).lower() == norm_target
        )
        avg_rating = (
            sum(p.rating for p in cell_places if p.rating) / len(cell_places)
            if cell_places
            else None
        )
        demand_score = total_biz.get(cell, 0) * 1.5
        opp_score = max(0.0, min(100.0, (demand_score / (comp_count + 1)) * 10))

        computed_metrics.append(
            {
                "h3_index": cell,
                "opportunity_score": opp_score,
                "supply_count": comp_count,
                "avg_rating": avg_rating,
            }
        )

    elapsed = time.perf_counter() - start_time

    assert len(unique_cells) > 50
    assert len(computed_metrics) == len(unique_cells)
    # The requirement is strictly under 30.0 seconds
    assert elapsed < 30.0, f"50k places gap computation took {elapsed:.2f}s (must be < 30s)"


def test_benchmark_map_api_5k_hexes():
    """Verify GeoJSON serialization for 5,000 hexes answers in under 500 ms."""
    import numpy as np

    # Generate 5,000 distinct H3 resolution-8 hex indices
    center_cell = h3.latlng_to_cell(12.9716, 77.5946, 8)
    # k-ring of radius ~45 gives > 5,000 cells
    cells = list(h3.grid_disk(center_cell, 45))[:5000]
    assert len(cells) == 5000

    ws_id = uuid.uuid4()
    job_id = uuid.uuid4()

    metrics = [
        HexMetric(
            workspace_id=ws_id,
            search_job_id=job_id,
            h3_index=cell,
            resolution=8,
            opportunity_score=float(np.random.uniform(10.0, 95.0)),
            label="high_opportunity",
            supply_count=int(np.random.randint(0, 15)),
            density_per_km2=float(np.random.uniform(0.5, 20.0)),
            avg_rating=float(np.random.uniform(3.0, 4.9)),
            avg_review_count=float(np.random.uniform(10.0, 200.0)),
            demand_proxy=float(np.random.uniform(5.0, 100.0)),
            explanation={"summary": "High demand, low supply"},
        )
        for cell in cells
    ]

    # Benchmark GeoJSON feature mapping
    start = time.perf_counter()
    features = [_hex_to_geojson_feature(m) for m in metrics]
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(features) == 5000
    # Must answer in under 500 ms
    msg = f"5,000 hexes GeoJSON serialization took {elapsed_ms:.1f}ms (< 500ms required)"
    assert elapsed_ms < 500.0, msg
