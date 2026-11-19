"""Email validation: RFC syntax, generic mailbox tagging, and bounded concurrent MX checking."""

import concurrent.futures
import logging
import re

import dns.resolver
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# RFC 5322 compliant simplified syntax regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

GENERIC_MAILBOX_PREFIXES: set[str] = {
    "info",
    "contact",
    "support",
    "hello",
    "admin",
    "help",
    "office",
    "sales",
    "inquiry",
    "enquiry",
    "mail",
    "team",
    "billing",
    "careers",
    "jobs",
    "press",
    "customercare",
    "service",
    "frontdesk",
}

# In-memory domain MX cache across runs
_MX_CACHE: dict[str, bool] = {}


class EmailValidationResult(BaseModel):
    """Validation outcome for an email address."""

    clean_email: str | None
    domain: str | None
    is_valid_syntax: bool
    has_valid_mx: bool
    is_generic: bool


def check_domain_mx(
    domain: str,
    timeout: float = 2.0,
    cache: dict[str, bool] | None = None,
) -> bool:
    """Verify if a domain possesses valid Mail Exchange (MX) DNS records.

    Caches results per domain to minimize DNS lookups.
    """
    clean_domain = domain.strip().lower()
    active_cache = cache if cache is not None else _MX_CACHE

    if clean_domain in active_cache:
        return active_cache[clean_domain]

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    has_mx = False
    try:
        answers = resolver.resolve(clean_domain, "MX")
        has_mx = len(answers) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        # RFC 5321 fallback: check for an A record if MX is absent
        try:
            a_records = resolver.resolve(clean_domain, "A")
            has_mx = len(a_records) > 0
        except Exception:
            has_mx = False
    except (dns.exception.Timeout, Exception) as exc:
        logger.debug("DNS MX lookup failed for domain %s: %s", clean_domain, exc)
        has_mx = False

    active_cache[clean_domain] = has_mx
    return has_mx


def batch_check_mx_records(
    domains: set[str] | list[str],
    max_workers: int = 10,
    timeout: float = 2.0,
    mx_cache: dict[str, bool] | None = None,
) -> dict[str, bool]:
    """Check MX records for a set of domains concurrently with bounded concurrency."""
    active_cache = mx_cache if mx_cache is not None else _MX_CACHE
    to_check = [d.strip().lower() for d in domains if d and d.strip().lower() not in active_cache]

    if to_check:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_domain = {
                executor.submit(check_domain_mx, d, timeout, active_cache): d for d in to_check
            }
            for future in concurrent.futures.as_completed(future_to_domain):
                d = future_to_domain[future]
                try:
                    active_cache[d] = future.result()
                except Exception:
                    active_cache[d] = False

    return active_cache


def validate_email_address(
    raw_email: str | None,
    check_mx: bool = True,
    mx_cache: dict[str, bool] | None = None,
    timeout: float = 2.0,
) -> EmailValidationResult:
    """Validate a single email address for syntax, generic naming, and optional MX."""
    if not raw_email or not raw_email.strip():
        return EmailValidationResult(
            clean_email=None,
            domain=None,
            is_valid_syntax=False,
            has_valid_mx=False,
            is_generic=False,
        )

    clean_email = raw_email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        return EmailValidationResult(
            clean_email=clean_email,
            domain=None,
            is_valid_syntax=False,
            has_valid_mx=False,
            is_generic=False,
        )

    local_part, domain = clean_email.split("@", 1)
    is_generic = local_part in GENERIC_MAILBOX_PREFIXES

    has_valid_mx = False
    if check_mx:
        has_valid_mx = check_domain_mx(domain, timeout=timeout, cache=mx_cache)

    return EmailValidationResult(
        clean_email=clean_email,
        domain=domain,
        is_valid_syntax=True,
        has_valid_mx=has_valid_mx,
        is_generic=is_generic,
    )


def validate_emails_batch(
    raw_emails: list[str | None],
    max_workers: int = 10,
    timeout: float = 2.0,
    mx_cache: dict[str, bool] | None = None,
) -> list[EmailValidationResult]:
    """Validate a batch of emails concurrently with bounded worker threads.

    Pre-fetches MX records for all unique domains concurrently so large batches
    (e.g. 5,000 places) never bottleneck.
    """
    active_cache = mx_cache if mx_cache is not None else _MX_CACHE

    # Collect unique domains requiring MX lookups
    unique_domains: set[str] = set()
    cleaned_candidates: list[tuple[str, str, str] | None] = []

    for raw in raw_emails:
        if not raw or not raw.strip():
            cleaned_candidates.append(None)
            continue
        cleaned = raw.strip().lower()
        if EMAIL_REGEX.match(cleaned):
            local_part, domain = cleaned.split("@", 1)
            cleaned_candidates.append((cleaned, local_part, domain))
            if domain not in active_cache:
                unique_domains.add(domain)
        else:
            cleaned_candidates.append(None)

    # Perform concurrent domain MX lookups with bounded concurrency
    if unique_domains:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_domain = {
                executor.submit(check_domain_mx, d, timeout, active_cache): d
                for d in unique_domains
            }
            for future in concurrent.futures.as_completed(future_to_domain):
                d = future_to_domain[future]
                try:
                    active_cache[d] = future.result()
                except Exception:
                    active_cache[d] = False

    # Build results from cache
    results: list[EmailValidationResult] = []
    for cand in cleaned_candidates:
        if cand is None:
            results.append(
                EmailValidationResult(
                    clean_email=None,
                    domain=None,
                    is_valid_syntax=False,
                    has_valid_mx=False,
                    is_generic=False,
                )
            )
        else:
            email, local_part, domain = cand
            results.append(
                EmailValidationResult(
                    clean_email=email,
                    domain=domain,
                    is_valid_syntax=True,
                    has_valid_mx=active_cache.get(domain, False),
                    is_generic=local_part in GENERIC_MAILBOX_PREFIXES,
                )
            )

    return results
