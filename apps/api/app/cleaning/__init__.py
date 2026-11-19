"""Data cleaning, normalisation, and deduplication package."""

from app.cleaning.duplicates import detect_and_merge_duplicates
from app.cleaning.email import EmailValidationResult, validate_email_address
from app.cleaning.phone import normalize_phone_number
from app.cleaning.pipeline import clean_and_normalize_job_places
from app.cleaning.taxonomy import normalize_category
from app.cleaning.website import WebsiteNormalizationResult, normalize_website

__all__ = [
    "EmailValidationResult",
    "WebsiteNormalizationResult",
    "clean_and_normalize_job_places",
    "detect_and_merge_duplicates",
    "normalize_category",
    "normalize_phone_number",
    "normalize_website",
    "validate_email_address",
]
