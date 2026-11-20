"""Field-level allow-list for public business information.

Ensures that only strictly public, non-personal business attributes are retained
in accordance with privacy legislation (DPDP Act, GDPR). Any personal, private,
or extraneous scraping session metadata is filtered out.
"""

from typing import Any

# Allowed keys in raw metadata dictionaries
PUBLIC_BUSINESS_ALLOWLIST: set[str] = {
    # Place identity
    "title",
    "name",
    "place_id",
    "cid",
    "data_id",
    "provider",
    "provider_place_id",
    # Classification
    "category",
    "normalized_category",
    "description",
    # Public contact & presence
    "address",
    "phone",
    "phone_e164",
    "website",
    "website_domain",
    "email",
    "emails",
    # Public metrics & operations
    "review_rating",
    "rating",
    "review_count",
    "price_range",
    "price_level",
    "latitude",
    "longitude",
    "open_hours",
    "opening_hours",
    "status",
    "permanently_closed",
    "is_closed",
    # Public reviews list
    "user_reviews",
    # Derived data-quality and lead-scoring flags
    "has_real_website",
    "is_social_media_only",
    "has_named_email",
    "has_generic_email",
    "email_mx_valid",
}

# Allowed fields within public review items
ALLOWED_REVIEW_FIELDS: set[str] = {
    "author_name",
    "rating",
    "text",
    "published_at",
    "owner_replied",
}


def sanitize_raw_business_data(raw_data: dict[str, Any] | None) -> dict[str, Any]:
    """Filter a raw scraped dictionary against the public business allow-list.

    Any unlisted fields (such as internal scraper cookies, tracker tokens, personal
    metadata) are discarded.
    """
    if not raw_data or not isinstance(raw_data, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in raw_data.items():
        if key in PUBLIC_BUSINESS_ALLOWLIST:
            sanitized[key] = value

    return sanitized


def sanitize_review_item(review_data: dict[str, Any]) -> dict[str, Any]:
    """Ensure a review dictionary contains only public review fields."""
    return {k: v for k, v in review_data.items() if k in ALLOWED_REVIEW_FIELDS}
