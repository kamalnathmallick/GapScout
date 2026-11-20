"""Lead feature extraction pipeline.

Extracts deterministic and neighborhood features for a place, versioned as 'v1'.
Stored in lead_features.features JSONB.
"""

import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HexMetric, Place, PlaceReview

FEATURE_VERSION = "v1"


def extract_lead_features(
    session: Session,
    place: Place,
    hex_metric: HexMetric | None = None,
    nearest_competitor_dist_m: float | None = None,
) -> dict[str, Any]:
    """Extract standard v1 features for a given place."""
    raw = place.raw if isinstance(place.raw, dict) else {}

    # 1. Place basic facts
    category = place.normalized_category or place.category or "general"
    rating = float(place.rating) if place.rating is not None else None
    review_count = int(place.review_count or 0)
    log_review_count = round(math.log1p(review_count), 4)

    # 2. Digital presence & contactability
    is_social_only = bool(raw.get("is_social_only", False))
    has_real_website = bool(place.website and not is_social_only)
    website_is_https = bool(place.website and place.website.lower().startswith("https://"))
    has_phone = bool(place.phone_e164)

    is_named_email = bool(raw.get("is_named_email", False))
    has_email = bool(place.email)
    has_named_email = bool(has_email and is_named_email)
    has_generic_email = bool(has_email and not is_named_email)

    price_level = int(place.price_level) if place.price_level is not None else None

    # Hours complete check
    hours_complete = bool(raw.get("hours") or raw.get("opening_hours") or raw.get("working_hours"))

    # 3. Reviews analysis
    reviews = (
        session.execute(select(PlaceReview).where(PlaceReview.place_id == place.id)).scalars().all()
    )

    total_reviews_sample = len(reviews)
    owner_replies = sum(1 for r in reviews if r.owner_replied)
    owner_reply_rate = (
        round(owner_replies / total_reviews_sample, 4) if total_reviews_sample > 0 else 0.0
    )

    negative_reviews = sum(1 for r in reviews if r.rating is not None and r.rating <= 3)
    negative_review_share = (
        round(negative_reviews / total_reviews_sample, 4) if total_reviews_sample > 0 else 0.0
    )

    # Days since most recent review
    now_utc = datetime.now(UTC)
    most_recent_review_date = None
    for r in reviews:
        if r.published_at:
            pub = r.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=UTC)
            if most_recent_review_date is None or pub > most_recent_review_date:
                most_recent_review_date = pub

    days_since_last_review: int | None = None
    if most_recent_review_date:
        days_since_last_review = max(0, (now_utc - most_recent_review_date).days)

    # 4. Neighborhood & Hex metrics
    hex_opportunity_score: float | None = None
    hex_supply_count: int = 0
    hex_demand_proxy: float | None = None

    if hex_metric:
        hex_opportunity_score = hex_metric.opportunity_score
        hex_supply_count = hex_metric.supply_count
        hex_demand_proxy = hex_metric.demand_proxy
    elif place.h3_r8:
        # Try fetching hex metric directly
        hex_row = session.execute(
            select(HexMetric).where(
                HexMetric.workspace_id == place.workspace_id,
                HexMetric.h3_index == place.h3_r8,
            )
        ).scalar_one_or_none()
        if hex_row:
            hex_opportunity_score = hex_row.opportunity_score
            hex_supply_count = hex_row.supply_count
            hex_demand_proxy = hex_row.demand_proxy

    # Nearest competitor distance
    distance_to_nearest_competitor_m = (
        round(nearest_competitor_dist_m, 1) if nearest_competitor_dist_m is not None else None
    )

    return {
        "feature_version": FEATURE_VERSION,
        "category": category,
        "rating": rating,
        "review_count": review_count,
        "log_review_count": log_review_count,
        "has_real_website": has_real_website,
        "website_is_https": website_is_https,
        "has_phone": has_phone,
        "has_named_email": has_named_email,
        "has_generic_email": has_generic_email,
        "price_level": price_level,
        "hours_complete": hours_complete,
        "owner_reply_rate": owner_reply_rate,
        "negative_review_share": negative_review_share,
        "days_since_last_review": days_since_last_review,
        "hex_opportunity_score": hex_opportunity_score,
        "hex_supply_count": hex_supply_count,
        "hex_demand_proxy": hex_demand_proxy,
        "distance_to_nearest_competitor_m": distance_to_nearest_competitor_m,
        "website_audit_score": None,  # Prompt 11 enrichment placeholder
        "number_of_review_pain_themes": None,  # Prompt 11 enrichment placeholder
    }
