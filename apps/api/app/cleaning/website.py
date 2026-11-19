"""Website URL cleaning, tracking parameter stripping, and social-only detection."""

import urllib.parse

from pydantic import BaseModel

SOCIAL_MEDIA_DOMAINS: set[str] = {
    "instagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "wa.me",
    "whatsapp.com",
    "tiktok.com",
    "youtube.com",
    "linktr.ee",
}

TRACKING_QUERY_PARAMS: set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "ref",
    "source",
    "rwg_token",
    "opi",
    "sa",
    "ved",
    "usg",
}


class WebsiteNormalizationResult(BaseModel):
    """Normalized website URL and domain evaluation."""

    clean_url: str | None
    domain: str | None
    is_social_media_only: bool
    has_real_website: bool


def normalize_website(raw_url: str | None) -> WebsiteNormalizationResult:
    """Normalize a website URL, strip tracking query params, and extract the domain.

    Flags social media pages (Instagram, Facebook, etc.) as having no real website.
    """
    if not raw_url or not raw_url.strip():
        return WebsiteNormalizationResult(
            clean_url=None,
            domain=None,
            is_social_media_only=False,
            has_real_website=False,
        )

    url_str = raw_url.strip()

    # Prepend https:// if scheme is missing
    if not url_str.lower().startswith(("http://", "https://")):
        url_str = f"https://{url_str}"

    try:
        parsed = urllib.parse.urlsplit(url_str)
    except ValueError:
        return WebsiteNormalizationResult(
            clean_url=None,
            domain=None,
            is_social_media_only=False,
            has_real_website=False,
        )

    # Extract clean domain
    netloc = parsed.netloc.lower()
    if ":" in netloc:
        netloc = netloc.split(":")[0]

    domain = netloc
    if domain.startswith("www."):
        domain = domain[4:]

    if not domain or "." not in domain:
        return WebsiteNormalizationResult(
            clean_url=None,
            domain=None,
            is_social_media_only=False,
            has_real_website=False,
        )

    # Check social-media-only status
    # Match domain or parent domain (e.g. m.facebook.com -> facebook.com)
    is_social = any(domain == s or domain.endswith(f".{s}") for s in SOCIAL_MEDIA_DOMAINS)
    has_real_site = not is_social

    # Filter tracking query parameters (strip all query params for social links)
    if is_social:
        new_query = ""
    else:
        query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        clean_params = [(k, v) for k, v in query_params if k.lower() not in TRACKING_QUERY_PARAMS]
        new_query = urllib.parse.urlencode(clean_params)

    # Reconstruct cleaned URL without tracking or fragment, normalizing to domain
    path = parsed.path or "/"
    clean_url = urllib.parse.urlunsplit(
        (parsed.scheme.lower() or "https", domain, path, new_query, "")
    ).rstrip("?")

    return WebsiteNormalizationResult(
        clean_url=clean_url,
        domain=domain,
        is_social_media_only=is_social,
        has_real_website=has_real_site,
    )
