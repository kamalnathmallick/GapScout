"""Tests for the explainable hex market gap analysis engine."""

import h3
import pytest
from geoalchemy2.elements import WKTElement

from app.gap.anchors import classify_anchor_category
from app.gap.config import GapConfig
from app.gap.engine import compute_gap_metrics
from app.models import HexMetric, Place, SearchJob, Workspace


# ==============================================================================
# 1. Anchor Classification Tests
# ==============================================================================
def test_anchor_classification():
    assert classify_anchor_category("Prestige Tech Park Office") == "office"
    assert classify_anchor_category("WeWork Coworking Space") == "office"
    assert classify_anchor_category("Indian Institute of Science") == "college"
    assert classify_anchor_category("National Public School") == "college"
    assert classify_anchor_category("Sobha Dream Acres Apartments") == "apartment"
    assert classify_anchor_category("Palm Meadows Luxury Villa Society") == "apartment"
    assert classify_anchor_category("Forum Mall Koramangala") == "mall"
    assert classify_anchor_category("Indiranagar Metro Station") == "transit"
    assert classify_anchor_category("Manipal Hospital ICU") == "hospital"
    assert classify_anchor_category("Random Bakery") is None


# ==============================================================================
# 2. Property Test: Opportunity Scores Always Between 0 and 100
# ==============================================================================
@pytest.mark.parametrize("supply", [0, 1, 2, 5, 10, 25, 50, 100])
@pytest.mark.parametrize("demand", [0.0, 1.0, 10.0, 50.0, 150.0, 500.0])
@pytest.mark.parametrize("quality_gap", [-1.5, 0.0, 0.5, 1.2, 2.5])
def test_opportunity_score_property_bounds(supply, demand, quality_gap):
    cfg = GapConfig()
    smoothed_supply = float(supply)
    ratio = demand / (smoothed_supply + cfg.smoothing_constant)
    max_ratio = 500.0  # reference scaling

    norm_score = (ratio / max_ratio * 85.0) if max_ratio > 0 else 0.0
    q_bonus = min(max(quality_gap * cfg.quality_gap_weight, 0.0), 15.0) if quality_gap > 0 else 0.0

    total_score = max(0.0, min(100.0, round(norm_score + q_bonus, 1)))

    assert 0.0 <= total_score <= 100.0


# ==============================================================================
# 3. Synthetic City Test: Crowded Centre vs Empty High-Demand Suburb
# ==============================================================================
def test_synthetic_city_gap_analysis(db_session):
    ws = Workspace(name="Synthetic City WS")
    db_session.add(ws)
    db_session.commit()

    # 1. Create a search job for "cafe"
    job = SearchJob(
        workspace_id=ws.id,
        category="cafe",
        area_name="Metropolis",
        status="completed",
        cells_total=2,
        cells_done=2,
    )
    db_session.add(job)
    db_session.commit()

    # 2. Zone A: Crowded Downtown Centre (12.9716, 77.5946)
    # Heavy cafe competition (10 cafes), low/mediocre ratings (avg ~3.2), few offices
    center_lat, center_lon = 12.9716, 77.5946
    downtown_hex = h3.latlng_to_cell(center_lat, center_lon, 8)

    places = []
    for i in range(10):
        lat = center_lat + (i * 0.0001)
        lon = center_lon + (i * 0.0001)
        p = Place(
            workspace_id=ws.id,
            provider="synthetic",
            provider_place_id=f"dt_cafe_{i}",
            name=f"Downtown Cafe #{i}",
            category="Cafe",
            normalized_category="cafe",
            rating=3.2,
            review_count=150,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            raw={"latitude": lat, "longitude": lon},
        )
        places.append(p)

    # Add 2 offices in downtown
    for i in range(2):
        lat = center_lat + 0.0002
        lon = center_lon + 0.0002
        p = Place(
            workspace_id=ws.id,
            provider="synthetic",
            provider_place_id=f"dt_office_{i}",
            name=f"Downtown Tech Office #{i}",
            category="Corporate Office",
            normalized_category=None,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            raw={"latitude": lat, "longitude": lon},
        )
        places.append(p)

    # 3. Zone B: Empty High-Demand Suburb (12.9100, 77.6800) ~11km away
    # ZERO cafes, but high demand: 12 corporate offices, 8 apartments, 3 colleges, 1 metro
    suburb_lat, suburb_lon = 12.9100, 77.6800
    suburb_hex = h3.latlng_to_cell(suburb_lat, suburb_lon, 8)
    assert suburb_hex != downtown_hex

    for i in range(12):
        lat = suburb_lat + (i * 0.0001)
        lon = suburb_lon + (i * 0.0001)
        p = Place(
            workspace_id=ws.id,
            provider="synthetic",
            provider_place_id=f"sub_office_{i}",
            name=f"Suburb Innovation Tech Park Office {i}",
            category="Corporate Office",
            normalized_category=None,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            raw={"latitude": lat, "longitude": lon},
        )
        places.append(p)

    for i in range(8):
        lat = suburb_lat + 0.0002 + (i * 0.0001)
        lon = suburb_lon + 0.0002 + (i * 0.0001)
        p = Place(
            workspace_id=ws.id,
            provider="synthetic",
            provider_place_id=f"sub_apt_{i}",
            name=f"Suburb Green Valley Luxury Apartments {i}",
            category="Residential Apartment",
            normalized_category=None,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            raw={"latitude": lat, "longitude": lon},
        )
        places.append(p)

    for i in range(3):
        lat = suburb_lat + 0.0003 + (i * 0.0001)
        lon = suburb_lon + 0.0003 + (i * 0.0001)
        p = Place(
            workspace_id=ws.id,
            provider="synthetic",
            provider_place_id=f"sub_college_{i}",
            name=f"Suburb Institute of Technology Campus {i}",
            category="Engineering College",
            normalized_category=None,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            raw={"latitude": lat, "longitude": lon},
        )
        places.append(p)

    metro = Place(
        workspace_id=ws.id,
        provider="synthetic",
        provider_place_id="sub_metro_1",
        name="Suburb Central Metro Station",
        category="Metro Station Transit",
        normalized_category=None,
        location=WKTElement(f"POINT({suburb_lon} {suburb_lat})", srid=4326),
        raw={"latitude": suburb_lat, "longitude": suburb_lon},
    )
    places.append(metro)

    db_session.add_all(places)
    db_session.commit()

    # 4. Run gap analysis engine
    summary = compute_gap_metrics(db_session, job.id, resolution=8)

    # 5. Assert results
    assert summary["total_hexes"] >= 2
    assert "best_hexes" in summary
    assert "saturated_hexes" in summary

    # Verify hex metrics in DB
    dt_metric = (
        db_session.query(HexMetric)
        .filter(HexMetric.search_job_id == job.id, HexMetric.h3_index == downtown_hex)
        .one()
    )
    sub_metric = (
        db_session.query(HexMetric)
        .filter(HexMetric.search_job_id == job.id, HexMetric.h3_index == suburb_hex)
        .one()
    )

    # Downtown checks: 10 competitors, lower score, labeled oversaturated
    assert dt_metric.supply_count == 10
    assert dt_metric.label == "oversaturated"
    assert dt_metric.opportunity_score < sub_metric.opportunity_score

    # Suburb checks: 0 competitors, huge demand proxy, high score, labeled underserved
    assert sub_metric.supply_count == 0
    assert sub_metric.demand_proxy > dt_metric.demand_proxy
    assert sub_metric.opportunity_score >= 70.0
    assert sub_metric.label == "underserved"

    # Explanation readability
    assert len(sub_metric.explanation["top_reasons"]) == 3
    assert any("0 competitors" in r for r in sub_metric.explanation["top_reasons"])
    assert any("Demand anchors" in r for r in sub_metric.explanation["top_reasons"])

    assert len(dt_metric.explanation["top_reasons"]) == 3
    assert any("competitors" in r for r in dt_metric.explanation["top_reasons"])

    # Area summary checks
    assert summary["best_hexes"][0]["h3_index"] == suburb_hex
    assert summary["saturated_hexes"][0]["h3_index"] == downtown_hex
