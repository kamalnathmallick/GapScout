"""Rule-based lead scoring engine (Cold-Start Model).

Evaluates 5 explainable components (Pain, Fit, Timing, Reachability, Evidence)
to produce a transparent 0-100 score and structured breakdown for sales outreach.
"""

from typing import Any

from app.models import OfferProfile, Place
from app.scoring.config import ScoringConfig, load_scoring_config


def compute_pain_component(features: dict[str, Any], config: ScoringConfig) -> tuple[float, str]:
    """Evaluate visible operational and digital pain points (max 25.0)."""
    p = config.pain
    points = 0.0
    reasons: list[str] = []

    has_real_website = features.get("has_real_website", False)
    website_is_https = features.get("website_is_https", False)
    rating = features.get("rating")
    negative_review_share = features.get("negative_review_share", 0.0)
    owner_reply_rate = features.get("owner_reply_rate", 0.0)

    # 1. No website or non-HTTPS website
    if not has_real_website:
        points += p.no_website_points
        reasons.append("No official website detected")
    elif not website_is_https:
        points += p.not_https_points
        reasons.append("Insecure HTTP website without SSL")

    # 2. Low rating
    if rating is not None and rating <= p.low_rating_threshold:
        points += p.low_rating_points
        reasons.append(f"Sub-par customer rating ({rating:.1f}/5.0)")

    # 3. Unanswered negative reviews
    if negative_review_share > 0.05 and owner_reply_rate < 0.25:
        points += p.unanswered_negative_reviews_points
        reasons.append("Unanswered negative reviews with low owner reply rate")

    score = min(points, config.weights.pain)
    if not reasons:
        reason = "Established digital presence with healthy rating and few public pain signals."
    else:
        reason = "; ".join(reasons) + "."

    return round(score, 1), reason


def compute_fit_component(
    features: dict[str, Any],
    place: Place,
    offer_profile: OfferProfile | None,
    config: ScoringConfig,
) -> tuple[float, str]:
    """Evaluate alignment with workspace Offer Profile (max 25.0)."""
    f = config.fit
    points = 0.0
    reasons: list[str] = []

    category = (features.get("category") or "").lower()
    rating = features.get("rating")

    if offer_profile:
        target_categories = [c.lower() for c in (offer_profile.target_categories or [])]
        target_regions = [r.lower() for r in (offer_profile.target_regions or [])]
        min_rating = offer_profile.min_rating
        max_rating = offer_profile.max_rating

        # Category match
        if not target_categories or category in target_categories:
            points += f.category_match_points
            reasons.append(f"Category '{category}' directly matches target offering")
        else:
            reasons.append(f"Category '{category}' is outside primary target focus")

        # Rating range match
        in_rating_range = True
        if min_rating is not None and rating is not None and rating < min_rating:
            in_rating_range = False
        if max_rating is not None and rating is not None and rating > max_rating:
            in_rating_range = False

        if in_rating_range and rating is not None:
            points += f.rating_range_points
            reasons.append("Rating falls within ideal prospect profile")

        # Region match
        address = (place.address or "").lower()
        if target_regions:
            matched_region = any(reg in address for reg in target_regions)
            if matched_region:
                points += f.region_match_points
                reasons.append("Located within targeted geographic territory")
        else:
            # If no target regions specified, grant regional points by default
            points += f.region_match_points
    else:
        # Default cold-start fit
        points += f.default_category_points
        if rating is not None and 2.5 <= rating <= 4.5:
            points += f.default_rating_points
        reasons.append("Standard commercial business fit (no custom Offer Profile configured)")

    score = min(points, config.weights.fit)
    reason = "; ".join(reasons) + "." if reasons else "Compatible commercial profile."
    return round(score, 1), reason


def compute_timing_component(features: dict[str, Any], config: ScoringConfig) -> tuple[float, str]:
    """Evaluate urgency and timing triggers (max 15.0)."""
    t = config.timing
    points = 0.0
    reasons: list[str] = []

    days_since_last_review = features.get("days_since_last_review")
    negative_review_share = features.get("negative_review_share", 0.0)
    review_count = features.get("review_count", 0)
    hex_opportunity_score = features.get("hex_opportunity_score")

    # 1. Recent customer dissatisfaction
    if (
        days_since_last_review is not None
        and days_since_last_review <= t.recent_review_days_threshold
        and negative_review_share > 0.0
    ):
        points += t.recent_negative_review_points
        reasons.append("Recent negative reviews within last 90 days indicate pressing urgency")

    # 2. Relatively new business
    if review_count < 15:
        points += t.new_business_points
        reasons.append("Early-stage establishment looking to ramp up local visibility")

    # 3. High opportunity neighborhood
    if (
        hex_opportunity_score is not None
        and hex_opportunity_score >= t.high_opportunity_hex_threshold
    ):
        points += t.high_opportunity_hex_points
        reasons.append(
            f"Situated in high-opportunity underserved hex (score {hex_opportunity_score:.0f})"
        )

    score = min(points, config.weights.timing)
    if not reasons:
        reason = "Established operating cadence with no urgent recent triggers."
    else:
        reason = "; ".join(reasons) + "."

    return round(score, 1), reason


def compute_reachability_component(
    features: dict[str, Any], config: ScoringConfig
) -> tuple[float, str]:
    """Evaluate verified contact routes (max 20.0)."""
    r = config.reachability
    points = 0.0
    reasons: list[str] = []

    has_named_email = features.get("has_named_email", False)
    has_generic_email = features.get("has_generic_email", False)
    has_phone = features.get("has_phone", False)
    has_real_website = features.get("has_real_website", False)

    if has_named_email:
        points += r.named_email_points
        reasons.append("Direct named contact email verified")
    elif has_generic_email:
        points += r.generic_email_points
        reasons.append("General business inquiry email available")

    if has_phone:
        points += r.phone_points
        reasons.append("Verified E.164 phone line accessible")

    if has_real_website:
        points += r.social_or_website_points
        reasons.append("Web presence available for digital outreach")

    score = min(points, config.weights.reachability)
    if not reasons:
        reason = "No direct public contact routes detected."
    else:
        reason = "; ".join(reasons) + "."

    return round(score, 1), reason


def compute_evidence_component(
    features: dict[str, Any], place: Place, config: ScoringConfig
) -> tuple[float, str]:
    """Evaluate verifiable signal backing the score (max 15.0)."""
    e = config.evidence
    points = 0.0
    reasons: list[str] = []

    review_count = features.get("review_count", 0)
    hours_complete = features.get("hours_complete", False)
    owner_reply_rate = features.get("owner_reply_rate", 0.0)

    # 1. Location verified
    if place.location is not None and place.address:
        points += e.verified_location_points
        reasons.append("Geocoded physical coordinates and verified street address")

    # 2. Review volume
    if review_count >= e.high_review_count_threshold:
        points += e.high_review_count_points
        reasons.append(f"Statistically significant review volume ({review_count} reviews)")

    # 3. Complete hours
    if hours_complete:
        points += e.hours_complete_points
        reasons.append("Complete published operating hours")

    # 4. Owner engagement
    if owner_reply_rate > 0.1:
        points += e.has_engagement_points
        reasons.append("Confirmed owner presence responding to customer feedback")

    score = min(points, config.weights.evidence)
    reason = "Limited public footprint and signals." if not reasons else "; ".join(reasons) + "."

    return round(score, 1), reason


def score_lead(
    features: dict[str, Any],
    place: Place,
    offer_profile: OfferProfile | None = None,
    config: ScoringConfig | None = None,
) -> dict[str, Any]:
    """Compute overall 0-100 rule score and detailed component breakdown."""
    if config is None:
        config = load_scoring_config()

    pain_score, pain_reason = compute_pain_component(features, config)
    fit_score, fit_reason = compute_fit_component(features, place, offer_profile, config)
    timing_score, timing_reason = compute_timing_component(features, config)
    reach_score, reach_reason = compute_reachability_component(features, config)
    ev_score, ev_reason = compute_evidence_component(features, place, config)

    total = round(pain_score + fit_score + timing_score + reach_score + ev_score, 1)
    total = max(0.0, min(100.0, total))

    return {
        "final_score": total,
        "rule_score": total,
        "score_breakdown": {
            "total": total,
            "components": {
                "pain": {
                    "score": pain_score,
                    "max": config.weights.pain,
                    "reason": pain_reason,
                },
                "fit": {
                    "score": fit_score,
                    "max": config.weights.fit,
                    "reason": fit_reason,
                },
                "timing": {
                    "score": timing_score,
                    "max": config.weights.timing,
                    "reason": timing_reason,
                },
                "reachability": {
                    "score": reach_score,
                    "max": config.weights.reachability,
                    "reason": reach_reason,
                },
                "evidence": {
                    "score": ev_score,
                    "max": config.weights.evidence,
                    "reason": ev_reason,
                },
            },
        },
    }
