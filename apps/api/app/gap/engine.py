"""Explainable hex-level market gap analysis engine."""

import logging
import statistics
import uuid
from typing import Any

import h3
from geoalchemy2.types import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.cleaning.duplicates import haversine_distance_m
from app.cleaning.taxonomy import normalize_category
from app.gap.anchors import classify_anchor_category
from app.gap.config import GapConfig, load_gap_config
from app.models import HexMetric, Place, SearchJob

logger = logging.getLogger(__name__)


def compute_gap_metrics(
    db: Session,
    job_id: uuid.UUID,
    resolution: int = 8,
    config: GapConfig | None = None,
) -> dict[str, Any]:
    """Compute explainable hex-level opportunity metrics for a search job.

    Uses fast bulk-tuple SQL queries for PostGIS coordinates and H3 aggregations.
    """
    cfg = config or load_gap_config()
    job = db.get(SearchJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    target_category = job.category
    norm_target_cat = normalize_category(target_category) or target_category.strip().lower()
    workspace_id = job.workspace_id

    # 1. Bulk-fetch all places in workspace with valid coordinates (scalar tuples, fast)
    stmt = select(
        Place.id,
        Place.name,
        Place.category,
        Place.normalized_category,
        Place.rating,
        Place.review_count,
        Place.is_closed,
        func.ST_Y(cast(Place.location, Geometry)).label("lat"),
        func.ST_X(cast(Place.location, Geometry)).label("lon"),
    ).where(
        Place.workspace_id == workspace_id,
        Place.location.is_not(None),
    )
    rows = db.execute(stmt).all()

    # 2. Extract job bounding box hexes if bbox exists
    active_hexes: set[str] = set()
    if job.bbox is not None:
        try:
            bbox_coords = db.execute(
                select(
                    func.ST_YMin(cast(job.bbox, Geometry)),
                    func.ST_XMin(cast(job.bbox, Geometry)),
                    func.ST_YMax(cast(job.bbox, Geometry)),
                    func.ST_XMax(cast(job.bbox, Geometry)),
                )
            ).one()
            min_lat, min_lon, max_lat, max_lon = bbox_coords
            poly = h3.LatLngPoly(
                [
                    (min_lat, min_lon),
                    (max_lat, min_lon),
                    (max_lat, max_lon),
                    (min_lat, max_lon),
                ]
            )
            active_hexes.update(h3.polygon_to_cells(poly, resolution))
        except Exception as e:
            logger.warning("Could not extract bbox hexes for job %s: %s", job_id, e)

    # 3. Categorize places: competitors, anchors, and total businesses
    competitors = []
    anchors_by_hex: dict[str, dict[str, int]] = {}
    total_businesses_by_hex: dict[str, int] = {}
    hex_places_map: dict[str, list[Any]] = {}

    for row in rows:
        lat, lon = float(row.lat), float(row.lon)
        cell = h3.latlng_to_cell(lat, lon, resolution)
        active_hexes.add(cell)

        hex_places_map.setdefault(cell, []).append(row)
        if not row.is_closed:
            total_businesses_by_hex[cell] = total_businesses_by_hex.get(cell, 0) + 1

            # Match target category
            p_cat = (row.normalized_category or row.category or "").strip().lower()
            is_comp = (
                p_cat == norm_target_cat
                or (row.category and normalize_category(row.category) == norm_target_cat)
                or (target_category.lower() in p_cat)
            )
            if is_comp:
                competitors.append((cell, row, lat, lon))

            # Classify anchor category
            anchor_type = classify_anchor_category(row.category) or classify_anchor_category(
                row.name
            )
            if anchor_type:
                hex_anchors = anchors_by_hex.setdefault(cell, {})
                hex_anchors[anchor_type] = hex_anchors.get(anchor_type, 0) + 1

    # If no active hexes detected, return empty summary
    if not active_hexes:
        return {"total_hexes": 0, "best_hexes": [], "saturated_hexes": []}

    # 4. Compute competitor stats and area median rating
    all_comp_ratings = [
        c[1].rating for c in competitors if c[1].rating is not None and c[1].rating > 0
    ]
    area_median_rating = round(statistics.median(all_comp_ratings), 2) if all_comp_ratings else 4.0

    competitor_coords = [(c[2], c[3]) for c in competitors]
    hex_competitors: dict[str, list[Any]] = {}
    for cell, comp_row, _, _ in competitors:
        hex_competitors.setdefault(cell, []).append(comp_row)

    # 5. Calculate raw metrics per hex
    hex_data: dict[str, dict[str, Any]] = {}
    cat_anchor_weights = cfg.anchor_weights.get(
        norm_target_cat, cfg.anchor_weights.get("default", {})
    )
    total_anchors_found = sum(sum(counts.values()) for counts in anchors_by_hex.values())
    confidence = "high" if total_anchors_found > 0 else "low"

    for hex_id in active_hexes:
        center_lat, center_lon = h3.cell_to_latlng(hex_id)
        comps = hex_competitors.get(hex_id, [])
        supply_count = len(comps)

        # Hex area in km^2
        area_km2 = round(h3.cell_area(hex_id, unit="km^2"), 3)
        density = round(supply_count / area_km2, 2) if area_km2 > 0 else 0.0

        ratings = [c.rating for c in comps if c.rating is not None]
        avg_rating = round(statistics.mean(ratings), 2) if ratings else None

        review_counts = [c.review_count for c in comps if c.review_count is not None]
        avg_reviews = round(statistics.mean(review_counts), 1) if review_counts else None

        # Quality gap (how far avg rating sits below area median)
        quality_gap = round(area_median_rating - avg_rating, 2) if avg_rating is not None else 0.0

        # Distance to nearest competitor
        if supply_count > 0:
            nearest_comp_m = 0.0
        elif competitor_coords:
            nearest_comp_m = round(
                min(
                    haversine_distance_m(center_lat, center_lon, clat, clon)
                    for clat, clon in competitor_coords
                ),
                1,
            )
        else:
            nearest_comp_m = 9999.0

        # Demand proxy calculation
        # Count anchors in hex and 1-ring neighbours
        disk_neighbors = h3.grid_disk(hex_id, 1)
        if total_anchors_found > 0:
            demand_val = 0.0
            anchor_summary: dict[str, int] = {}
            for n_cell in disk_neighbors:
                counts = anchors_by_hex.get(n_cell, {})
                for atype, acount in counts.items():
                    w = cat_anchor_weights.get(atype, 1.0)
                    demand_val += acount * w
                    anchor_summary[atype] = anchor_summary.get(atype, 0) + acount
        else:
            # Fallback to total business count in disk
            disk_total = sum(total_businesses_by_hex.get(n_cell, 0) for n_cell in disk_neighbors)
            demand_val = float(disk_total)
            anchor_summary = {"businesses": int(demand_val)}

        hex_data[hex_id] = {
            "h3_index": hex_id,
            "supply_count": supply_count,
            "density_per_km2": density,
            "avg_rating": avg_rating,
            "avg_review_count": avg_reviews,
            "quality_gap": quality_gap,
            "nearest_competitor_m": nearest_comp_m,
            "demand_proxy": round(demand_val, 2),
            "anchor_summary": anchor_summary,
            "center_lat": center_lat,
            "center_lon": center_lon,
        }

    # 6. Apply k-ring (k=1) spatial smoothing to supply
    for hex_id, data in hex_data.items():
        neighbors = [n for n in h3.grid_disk(hex_id, 1) if n != hex_id and n in hex_data]
        if neighbors:
            avg_n_supply = sum(hex_data[n]["supply_count"] for n in neighbors) / len(neighbors)
        else:
            avg_n_supply = float(data["supply_count"])

        smoothed_supply = (1.0 - cfg.k_ring_weight) * data[
            "supply_count"
        ] + cfg.k_ring_weight * avg_n_supply
        data["smoothed_supply"] = round(smoothed_supply, 2)

    # 7. Opportunity Score (0 to 100)
    # Score = normalized(demand_proxy / (smoothed_supply + smoothing_constant)) + quality_gap_bonus
    raw_ratios: dict[str, float] = {}
    for hex_id, data in hex_data.items():
        ratio = data["demand_proxy"] / (data["smoothed_supply"] + cfg.smoothing_constant)
        raw_ratios[hex_id] = ratio

    max_ratio = max(raw_ratios.values()) if raw_ratios else 1.0

    for hex_id, data in hex_data.items():
        ratio = raw_ratios[hex_id]
        norm_score = (ratio / max_ratio * 85.0) if max_ratio > 0 else 0.0

        # Quality gap bonus (up to 15 points)
        q_bonus = 0.0
        if data["quality_gap"] > 0:
            q_bonus = min(data["quality_gap"] * cfg.quality_gap_weight, 15.0)

        total_score = norm_score + q_bonus
        # Clamp strictly between 0 and 100
        total_score = max(0.0, min(100.0, total_score))
        data["opportunity_score"] = round(total_score, 1)

    # 8. Quantile-based labeling ('underserved', 'balanced', 'oversaturated', 'insufficient_data')
    active_scores = [
        d["opportunity_score"]
        for d in hex_data.values()
        if d["demand_proxy"] > 0 or d["supply_count"] > 0
    ]

    if active_scores:
        sorted_scores = sorted(active_scores)
        n = len(sorted_scores)
        idx_p33 = int(n * cfg.quantiles.get("oversaturated_percentile", 0.33))
        idx_p67 = int(n * cfg.quantiles.get("underserved_percentile", 0.67))
        p33_thresh = sorted_scores[min(idx_p33, n - 1)]
        p67_thresh = sorted_scores[min(idx_p67, n - 1)]
    else:
        p33_thresh = 35.0
        p67_thresh = 65.0

    # 9. Formulate explanations and labels
    for hex_id, data in hex_data.items():
        score = data["opportunity_score"]
        supply = data["supply_count"]
        demand = data["demand_proxy"]

        if demand == 0 and supply == 0:
            label = "insufficient_data"
        elif score >= p67_thresh:
            label = "underserved"
        elif score <= p33_thresh:
            label = "oversaturated"
        else:
            label = "balanced"

        data["label"] = label

        # Formulate top 3 reasons
        reasons = []
        # Reason 1: Competition & proximity
        if supply == 0:
            if data["nearest_competitor_m"] >= 9999:
                reasons.append("0 competitors in entire area")
            else:
                dist_km = data["nearest_competitor_m"] / 1000.0
                reasons.append(f"0 competitors within {dist_km:.1f} km")
        elif supply == 1:
            reasons.append("Low competitor density (1 business in hex)")
        else:
            reasons.append(f"Crowded hex with {supply} competitors ({data['density_per_km2']}/km²)")

        # Reason 2: Demand anchors
        if total_anchors_found > 0:
            top_anchors = sorted(data["anchor_summary"].items(), key=lambda x: x[1], reverse=True)
            anchor_strs = [f"{count} {atype}s" for atype, count in top_anchors[:2]]
            if anchor_strs:
                reasons.append(f"Demand anchors: {', '.join(anchor_strs)} nearby")
            else:
                reasons.append(f"Demand proxy score: {demand:.1f} ({confidence} confidence)")
        else:
            reasons.append(
                f"Business density: {int(demand)} businesses nearby ({confidence} confidence)"
            )

        # Reason 3: Rating gap or customer sentiment
        if data["avg_rating"] is not None:
            if data["quality_gap"] > 0:
                reasons.append(
                    f"Quality gap: rating {data['avg_rating']} below median {area_median_rating}"
                )
            else:
                reasons.append(f"High local quality: rating avg {data['avg_rating']}")
        else:
            reasons.append("Uncontested opportunity: no existing customer ratings in hex")

        explanation = {
            "top_reasons": reasons[:3],
            "metrics": {
                "supply_count": supply,
                "density_per_km2": data["density_per_km2"],
                "smoothed_supply": data["smoothed_supply"],
                "demand_proxy": demand,
                "nearest_competitor_m": data["nearest_competitor_m"],
                "avg_rating": data["avg_rating"],
                "quality_gap": data["quality_gap"],
                "confidence": confidence,
            },
        }
        data["explanation"] = explanation

        # 10. Upsert into hex_metrics table
        upsert_stmt = (
            insert(HexMetric)
            .values(
                workspace_id=workspace_id,
                search_job_id=job_id,
                category=norm_target_cat,
                h3_index=hex_id,
                resolution=resolution,
                supply_count=supply,
                density_per_km2=data["density_per_km2"],
                avg_rating=data["avg_rating"],
                avg_review_count=data["avg_review_count"],
                demand_proxy=demand,
                opportunity_score=score,
                label=label,
                explanation=explanation,
                computed_at=func.now(),
            )
            .on_conflict_do_update(
                constraint="uq_hex_metrics_cell",
                set_={
                    "supply_count": supply,
                    "density_per_km2": data["density_per_km2"],
                    "avg_rating": data["avg_rating"],
                    "avg_review_count": data["avg_review_count"],
                    "demand_proxy": demand,
                    "opportunity_score": score,
                    "label": label,
                    "explanation": explanation,
                    "computed_at": func.now(),
                },
            )
        )
        db.execute(upsert_stmt)

    # 11. Produce Area Summary (best 3 and saturated 3)
    sorted_by_score = sorted(hex_data.values(), key=lambda d: d["opportunity_score"], reverse=True)
    best_3 = [
        {
            "h3_index": d["h3_index"],
            "opportunity_score": d["opportunity_score"],
            "label": d["label"],
            "reasons": d["explanation"]["top_reasons"],
        }
        for d in sorted_by_score[:3]
    ]

    # Saturated 3 (lowest scores among hexes with competitors or non-insufficient data)
    saturated_candidates = [
        d
        for d in sorted(hex_data.values(), key=lambda d: d["opportunity_score"])
        if d["label"] != "insufficient_data"
    ] or sorted_by_score[-3:]

    saturated_3 = [
        {
            "h3_index": d["h3_index"],
            "opportunity_score": d["opportunity_score"],
            "label": d["label"],
            "reasons": d["explanation"]["top_reasons"],
        }
        for d in saturated_candidates[:3]
    ]

    area_summary = {
        "job_id": str(job_id),
        "category": norm_target_cat,
        "resolution": resolution,
        "total_hexes": len(hex_data),
        "underserved_count": sum(1 for d in hex_data.values() if d["label"] == "underserved"),
        "balanced_count": sum(1 for d in hex_data.values() if d["label"] == "balanced"),
        "oversaturated_count": sum(1 for d in hex_data.values() if d["label"] == "oversaturated"),
        "insufficient_data_count": sum(
            1 for d in hex_data.values() if d["label"] == "insufficient_data"
        ),
        "area_median_rating": area_median_rating,
        "best_hexes": best_3,
        "saturated_hexes": saturated_3,
    }

    # Save summary in job.params["gap_summary"]
    job_params = dict(job.params) if isinstance(job.params, dict) else {}
    job_params["gap_summary"] = area_summary
    job.params = job_params
    db.commit()

    logger.info(
        "Computed gap metrics for job %s: %d hexes. Underserved: %d, Saturated: %d",
        job_id,
        len(hex_data),
        area_summary["underserved_count"],
        area_summary["oversaturated_count"],
    )
    return area_summary
