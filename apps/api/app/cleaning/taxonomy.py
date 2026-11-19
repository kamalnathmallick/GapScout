"""Category normalization into a controlled taxonomy."""

import difflib
import re

CONTROLLED_TAXONOMY: dict[str, list[str]] = {
    "cafe": [
        "cafe",
        "café",
        "coffee shop",
        "coffee store",
        "espresso bar",
        "coffee",
        "roastery",
        "tea room",
        "bakery cafe",
        "dessert cafe",
    ],
    "restaurant": [
        "restaurant",
        "dining",
        "bistro",
        "diner",
        "eatery",
        "food court",
        "fast food",
        "family restaurant",
        "pizzeria",
        "burger joint",
        "bar & grill",
        "asian restaurant",
        "italian restaurant",
        "north indian restaurant",
        "south indian restaurant",
    ],
    "gym": [
        "gym",
        "fitness center",
        "fitness club",
        "health club",
        "crossfit",
        "yoga studio",
        "pilates studio",
        "martial arts",
        "athletic club",
        "workout",
    ],
    "salon": [
        "salon",
        "hair salon",
        "beauty salon",
        "beauty parlor",
        "nail salon",
        "spa",
        "barber shop",
        "skin care clinic",
        "hairdresser",
    ],
    "dental clinic": [
        "dental clinic",
        "dentist",
        "dental care",
        "orthodontist",
        "dental surgery",
        "teeth clinic",
        "oral healthcare",
    ],
    "coaching centre": [
        "coaching centre",
        "coaching center",
        "coaching institute",
        "tuition centre",
        "tuition classes",
        "training institute",
        "test prep",
        "competitive exam coaching",
        "academy",
        "tutorials",
    ],
}


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def normalize_category(raw_category: str | None, threshold: float = 0.65) -> str | None:
    """Normalize a raw category string into a controlled taxonomy category.

    Uses exact keyword matching, substring lookup, and difflib sequence matching.
    """
    if not raw_category or not raw_category.strip():
        return None

    cleaned = _clean_text(raw_category)

    # 1. Exact or substring match in canonical keys or synonyms
    for canonical, synonyms in CONTROLLED_TAXONOMY.items():
        if cleaned == canonical or canonical in cleaned:
            return canonical
        for syn in synonyms:
            if syn in cleaned or cleaned in syn:
                return canonical

    # 2. Fuzzy sequence match across all synonyms
    best_match_category: str | None = None
    best_score = 0.0

    for canonical, synonyms in CONTROLLED_TAXONOMY.items():
        for syn in synonyms:
            ratio = difflib.SequenceMatcher(None, cleaned, syn).ratio()
            if ratio > best_score:
                best_score = ratio
                best_match_category = canonical

    if best_score >= threshold and best_match_category:
        return best_match_category

    # Fallback to cleaned primary word if not matched
    return None
