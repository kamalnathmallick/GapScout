"""Phone number validation and E.164 normalisation."""

import logging

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

logger = logging.getLogger(__name__)


def normalize_phone_number(
    raw_phone: str | None,
    default_region: str = "IN",
) -> str | None:
    """Normalize raw phone strings to E.164 format with +91 as default region.

    Validates the phone number according to carrier/regional rules.
    Invalid or unparseable numbers return None.
    """
    if not raw_phone or not raw_phone.strip():
        return None

    cleaned = raw_phone.strip()
    # Remove tel: prefix or common noisy prefixes
    if cleaned.lower().startswith("tel:"):
        cleaned = cleaned[4:].strip()

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if not phonenumbers.is_valid_number(parsed):
            logger.debug("Invalid phone number rejected: %s", raw_phone)
            return None

        formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        return formatted
    except NumberParseException:
        logger.debug("Failed to parse phone number: %s", raw_phone)
        return None
