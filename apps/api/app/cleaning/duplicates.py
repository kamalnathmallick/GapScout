"""Duplicate detection and merging based on fuzzy name matching and geographic distance."""

import difflib
import logging
import math
import re
from typing import Any

from geoalchemy2.shape import to_shape

from app.models import Place

logger = logging.getLogger(__name__)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geographic distance between two points in meters using Haversine formula."""
    r_earth = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_earth * c


def clean_name_for_comparison(name: str) -> str:
    """Normalize a business name for fuzzy comparison."""
    no_quotes = name.lower().replace("'", "").replace("\u2019", "")
    cleaned = re.sub(r"[^\w\s]", " ", no_quotes)
    # Remove common filler words in business names
    tokens = [w for w in cleaned.split() if w not in {"the", "and", "llc", "pvt", "ltd"}]
    return " ".join(tokens)


def are_names_fuzzy_match(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Check if two business names match fuzzily using SequenceMatcher and token containment."""
    n1 = clean_name_for_comparison(name1)
    n2 = clean_name_for_comparison(name2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True

    # 1. SequenceMatcher ratio
    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    if ratio >= threshold:
        return True

    # 2. Token containment (e.g. "Third Wave Coffee" in "Third Wave Coffee Roasters")
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    if len(tokens1) >= 2 and len(tokens2) >= 2:
        common = tokens1.intersection(tokens2)
        min_len = min(len(tokens1), len(tokens2))
        if len(common) >= min_len and (min_len / max(len(tokens1), len(tokens2))) >= 0.6:
            return True

    return False


def get_place_coords(place: Place | dict[str, Any]) -> tuple[float, float] | None:
    """Extract (latitude, longitude) from Place model or dict."""
    if isinstance(place, dict):
        lat = place.get("latitude") or place.get("lat")
        lon = place.get("longitude") or place.get("lng") or place.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        return None

    if place.location is not None:
        try:
            pt = to_shape(place.location)
            return float(pt.y), float(pt.x)
        except Exception:
            pass

    if isinstance(place.raw, dict):
        lat = place.raw.get("latitude") or place.raw.get("lat")
        lon = place.raw.get("longitude") or place.raw.get("lng")
        if lat is not None and lon is not None:
            try:
                return float(lat), float(lon)
            except (ValueError, TypeError):
                pass
    return None


def calculate_completeness_score(place: Place | dict[str, Any]) -> int:
    """Score place data richness to determine which duplicate should be the primary."""
    score = 0
    if isinstance(place, dict):
        if place.get("website"):
            score += 3
        if place.get("phone") or place.get("phone_e164"):
            score += 3
        if place.get("email"):
            score += 3
        if place.get("rating") is not None:
            score += 2
        if place.get("review_count", 0) > 0:
            score += min(place.get("review_count", 0), 10)
        if place.get("address"):
            score += 1
    else:
        if place.website:
            score += 3
        if place.phone_e164:
            score += 3
        if place.email:
            score += 3
        if place.rating is not None:
            score += 2
        if place.review_count > 0:
            score += min(place.review_count, 10)
        if place.address:
            score += 1
    return score


def detect_and_merge_duplicates(
    places: list[Place],
    max_distance_m: float = 50.0,
    name_similarity_threshold: float = 0.85,
) -> int:
    """Detect duplicate places within max_distance_m and name similarity threshold.

    The place with the higher completeness score is kept as primary and enriched
    with missing fields from secondary duplicates. Secondary duplicates are flagged
    in raw['is_duplicate'] = True and marked is_closed = True.

    Returns the number of duplicates flagged/merged.
    """
    if len(places) < 2:
        return 0

    # Extract coordinates
    coords_map: dict[Any, tuple[float, float] | None] = {p.id: get_place_coords(p) for p in places}

    duplicates_found = 0
    flagged_ids: set[Any] = set()

    for i in range(len(places)):
        p1 = places[i]
        if p1.id in flagged_ids:
            continue
        c1 = coords_map[p1.id]
        if not c1:
            continue

        for j in range(i + 1, len(places)):
            p2 = places[j]
            if p2.id in flagged_ids:
                continue
            c2 = coords_map[p2.id]
            if not c2:
                continue

            dist = haversine_distance_m(c1[0], c1[1], c2[0], c2[1])
            if dist > max_distance_m:
                continue

            if are_names_fuzzy_match(p1.name, p2.name, name_similarity_threshold):
                # Duplicate detected!
                score1 = calculate_completeness_score(p1)
                score2 = calculate_completeness_score(p2)

                primary, secondary = (p1, p2) if score1 >= score2 else (p2, p1)

                # Merge missing attributes from secondary to primary
                if not primary.website and secondary.website:
                    primary.website = secondary.website
                    primary.website_domain = secondary.website_domain
                if not primary.phone_e164 and secondary.phone_e164:
                    primary.phone_e164 = secondary.phone_e164
                if not primary.email and secondary.email:
                    primary.email = secondary.email
                if not primary.address and secondary.address:
                    primary.address = secondary.address

                # Flag secondary
                raw_dict = dict(secondary.raw) if isinstance(secondary.raw, dict) else {}
                raw_dict["is_duplicate"] = True
                raw_dict["duplicate_of_id"] = str(primary.id)
                secondary.raw = raw_dict
                secondary.is_closed = True

                flagged_ids.add(secondary.id)
                duplicates_found += 1
                logger.info(
                    "Duplicate detected (dist=%.1fm): '%s' and '%s'. Flagged %s.",
                    dist,
                    p1.name,
                    p2.name,
                    secondary.id,
                )

    return duplicates_found
