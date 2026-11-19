"""Data cleaning and normalisation pipeline for places."""

import logging
import uuid
from typing import Any

import h3
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cleaning.duplicates import detect_and_merge_duplicates, get_place_coords
from app.cleaning.email import (
    batch_check_mx_records,
    validate_email_address,
)
from app.cleaning.phone import normalize_phone_number
from app.cleaning.taxonomy import normalize_category
from app.cleaning.website import normalize_website
from app.models import Place, SearchJob

logger = logging.getLogger(__name__)


def clean_and_normalize_place(place: Place, mx_cache: dict[str, bool] | None = None) -> None:
    """Clean and normalize a single Place entity in-place."""
    # 1. Category normalisation
    if place.category:
        normalized_cat = normalize_category(place.category)
        if normalized_cat:
            place.normalized_category = normalized_cat

    # 2. Phone normalisation (E.164 with +91 default)
    raw_dict = place.raw if isinstance(place.raw, dict) else {}
    raw_phone = place.phone_e164 or raw_dict.get("phone")
    if raw_phone:
        normalized_phone = normalize_phone_number(raw_phone)
        place.phone_e164 = normalized_phone

    # 3. Website normalisation & domain extraction
    raw_website = place.website or raw_dict.get("website")
    web_res = normalize_website(raw_website)
    place.website = web_res.clean_url
    place.website_domain = web_res.domain

    # 4. Email validation & generic mailbox tagging
    raw_email = place.email or raw_dict.get("email")
    email_res = validate_email_address(raw_email, check_mx=True, mx_cache=mx_cache)
    if email_res.is_valid_syntax:
        place.email = email_res.clean_email
    else:
        place.email = None

    # 5. H3 resolution 8 computation
    coords = get_place_coords(place)
    if coords:
        lat, lon = coords
        try:
            place.h3_r8 = h3.latlng_to_cell(lat, lon, 8)
        except Exception as e:
            logger.warning("Failed to compute H3 index for place %s: %s", place.id, e)

    # 6. Check for permanently closed status in raw data
    raw_dict = dict(place.raw) if isinstance(place.raw, dict) else {}
    if (
        raw_dict.get("permanently_closed") is True
        or raw_dict.get("is_closed") is True
        or str(raw_dict.get("status", "")).lower() == "permanently closed"
    ):
        place.is_closed = True

    # Store derived flags in raw metadata for lead scoring and enrichment
    raw_dict["has_real_website"] = web_res.has_real_website
    raw_dict["is_social_media_only"] = web_res.is_social_media_only
    raw_dict["has_named_email"] = email_res.is_valid_syntax and not email_res.is_generic
    raw_dict["has_generic_email"] = email_res.is_valid_syntax and email_res.is_generic
    raw_dict["email_mx_valid"] = email_res.has_valid_mx
    place.raw = raw_dict


def generate_quality_report(places: list[Place], duplicates_removed: int) -> dict[str, Any]:
    """Generate a data-quality report for a list of places."""
    total_count = len(places)
    if total_count == 0:
        return {
            "total_places": 0,
            "open_places": 0,
            "closed_places": 0,
            "pct_with_website": 0.0,
            "pct_with_real_website": 0.0,
            "pct_with_phone": 0.0,
            "pct_with_email": 0.0,
            "pct_with_named_email": 0.0,
            "pct_rating_coverage": 0.0,
            "duplicates_removed": duplicates_removed,
        }

    open_count = sum(1 for p in places if not p.is_closed)
    closed_count = sum(1 for p in places if p.is_closed)
    with_website_count = sum(1 for p in places if p.website)
    with_real_website_count = sum(
        1 for p in places if isinstance(p.raw, dict) and p.raw.get("has_real_website")
    )
    with_phone_count = sum(1 for p in places if p.phone_e164)
    with_email_count = sum(1 for p in places if p.email)
    with_named_email_count = sum(
        1 for p in places if isinstance(p.raw, dict) and p.raw.get("has_named_email")
    )
    with_rating_count = sum(1 for p in places if p.rating is not None)

    return {
        "total_places": total_count,
        "open_places": open_count,
        "closed_places": closed_count,
        "pct_with_website": round((with_website_count / total_count) * 100, 1),
        "pct_with_real_website": round((with_real_website_count / total_count) * 100, 1),
        "pct_with_phone": round((with_phone_count / total_count) * 100, 1),
        "pct_with_email": round((with_email_count / total_count) * 100, 1),
        "pct_with_named_email": round((with_named_email_count / total_count) * 100, 1),
        "pct_rating_coverage": round((with_rating_count / total_count) * 100, 1),
        "duplicates_removed": duplicates_removed,
    }


def clean_and_normalize_job_places(
    db: Session,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    """Run data cleaning, normalization, duplicate detection, and quality report."""
    job = db.get(SearchJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Load all places belonging to this workspace
    # Note: places found during the job belong to job.workspace_id
    places_stmt = select(Place).where(Place.workspace_id == job.workspace_id)
    places = list(db.scalars(places_stmt).all())

    # Pre-warm MX cache for email domains concurrently
    domains_to_check = set()
    for p in places:
        raw_email = p.email or (p.raw.get("email") if isinstance(p.raw, dict) else None)
        if raw_email and "@" in raw_email:
            domain = raw_email.split("@")[-1].strip().lower()
            if domain:
                domains_to_check.add(domain)

    mx_cache = batch_check_mx_records(domains_to_check)

    # Clean and normalize each place
    for place in places:
        clean_and_normalize_place(place, mx_cache=mx_cache)

    # Detect and merge duplicates
    duplicates_removed = detect_and_merge_duplicates(places)

    # Generate quality report
    report = generate_quality_report(places, duplicates_removed)

    # Save quality report in search_jobs.params["quality_report"]
    job_params = dict(job.params) if isinstance(job.params, dict) else {}
    job_params["quality_report"] = report
    job.params = job_params

    db.commit()
    logger.info("Cleaned %d places for job %s. Report: %s", len(places), job_id, report)
    return report
