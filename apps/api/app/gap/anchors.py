"""Anchor categories and demand classification."""

import re

ANCHOR_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "office": [
        "office",
        "offices",
        "corporate",
        "commercial",
        "coworking",
        "tech park",
        "business park",
        "company",
        "enterprise",
    ],
    "college": [
        "college",
        "colleges",
        "university",
        "universities",
        "institute",
        "institutes",
        "campus",
        "school",
        "schools",
        "academy",
        "educational",
    ],
    "apartment": [
        "apartment",
        "apartments",
        "residential",
        "condo",
        "condos",
        "condominium",
        "condominiums",
        "housing",
        "society",
        "flat",
        "flats",
        "residence",
        "residences",
        "villa",
        "villas",
    ],
    "mall": [
        "mall",
        "malls",
        "shopping mall",
        "shopping center",
        "shopping centre",
        "supermarket",
        "supermarkets",
        "hypermarket",
        "market",
    ],
    "transit": [
        "metro",
        "bus stand",
        "bus stop",
        "train station",
        "railway",
        "transit",
        "subway",
    ],
    "hospital": [
        "hospital",
        "hospitals",
        "clinic",
        "clinics",
        "healthcare",
        "medical center",
        "medical centre",
        "nursing home",
    ],
}


def classify_anchor_category(category_or_name: str | None) -> str | None:
    """Classify a place into an anchor category (office, college, apartment, mall, etc.)."""
    if not category_or_name:
        return None

    text = category_or_name.lower()
    for anchor, keywords in ANCHOR_CATEGORY_PATTERNS.items():
        for kw in keywords:
            # Word boundary search
            if re.search(rf"\b{re.escape(kw)}\b", text):
                return anchor

    return None
