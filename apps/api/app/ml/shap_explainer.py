"""Explainability engine: extracts top-3 feature contributions per lead for explanation views."""

from typing import Any

FEATURE_REASONS = {
    "rating": (
        "Rating indicates service friction and high receptivity to improvements",
        "High rating establishes credibility and strong local reputation",
    ),
    "review_count": (
        "Low review volume makes business vulnerable to competitors",
        "Substantial review volume provides strong market presence and social proof",
    ),
    "has_named_email": (
        "No direct named email found",
        "Named decision-maker email available for direct contact",
    ),
    "has_generic_email": (
        "No email route detected",
        "Public email detected for outreach",
    ),
    "has_real_website": (
        "Missing official website represents a critical conversion gap",
        "Operational website provides baseline credibility",
    ),
    "hex_opportunity_score": (
        "Located in saturated market zone",
        "Located in underserved high-opportunity market hex",
    ),
    "website_audit_score": (
        "Website audit found technical and mobile conversion gaps",
        "Strong website ready for inbound traffic",
    ),
    "number_of_review_pain_themes": (
        "Few recurring customer complaints detected",
        "Multiple recurring customer complaint themes offer strong pitch angles",
    ),
}


def explain_lead_features(
    lead_features: dict[str, Any],
    feature_importances: dict[str, float] | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Compute top-k feature impacts and plain-English reasons for why a lead was ranked."""
    # Default feature importance weights if model importances not provided
    weights = feature_importances or {
        "rating": 0.25,
        "has_named_email": 0.20,
        "hex_opportunity_score": 0.20,
        "website_audit_score": 0.15,
        "number_of_review_pain_themes": 0.10,
        "has_real_website": 0.10,
    }

    scored_contributions: list[dict[str, Any]] = []

    for feature_name, weight in weights.items():
        val = lead_features.get(feature_name)
        if val is None:
            continue

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            continue

        # Determine signal direction
        # Lower rating = higher opportunity for pain
        if feature_name == "rating":
            is_positive = num_val < 4.0
            impact = abs(4.0 - num_val) * 25.0 * weight
        elif feature_name in {"has_named_email", "has_generic_email", "has_real_website"}:
            is_positive = num_val > 0.5
            impact = 15.0 * weight * (1.0 if is_positive else 0.5)
        elif feature_name in {"hex_opportunity_score", "website_audit_score"}:
            is_positive = num_val >= 50.0
            impact = (num_val / 100.0) * 20.0 * weight
        else:
            is_positive = num_val > 0.0
            impact = min(20.0, num_val * 5.0) * weight

        reasons = FEATURE_REASONS.get(feature_name)
        reason_text = (
            (reasons[1] if is_positive else reasons[0])
            if reasons
            else f"Significant {feature_name} signal ({num_val})"
        )

        scored_contributions.append(
            {
                "feature": feature_name,
                "impact": round(impact, 2),
                "direction": "positive" if is_positive else "negative",
                "value": num_val,
                "reason": reason_text,
            }
        )

    # Sort descending by impact magnitude
    scored_contributions.sort(key=lambda c: c["impact"], reverse=True)
    return scored_contributions[:top_k]
