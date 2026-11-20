"""Safe HTTP fetcher with strict SSRF defense, size caps, and deterministic signal extraction."""

import ipaddress
import logging
import re
import socket
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

MAX_WEBSITE_BYTES = 512 * 1024  # 512 KB
DEFAULT_TIMEOUT_SEC = 8.0
USER_AGENT = "GapScout/1.0 (+https://gapscout.app/bot; market intelligence)"

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class SSRFBlockedError(ValueError):
    """Raised when a URL attempts to connect to a private, loopback, or non-routable IP."""

    pass


class SafeFetcherError(Exception):
    """Base error for safe fetcher failures."""

    pass


def validate_url_and_check_ssrf(url: str) -> None:
    """Validate URL protocol and resolve hostname to ensure no private/loopback IPs are accessed."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFBlockedError(f"Unsupported scheme '{parsed.scheme}'; only http/https allowed")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedError("URL lacks a valid hostname")

    # Reject literal localhost
    if hostname.lower() in ("localhost", "localhost.localdomain", "broadcasthost"):
        raise SSRFBlockedError(f"Access to '{hostname}' is prohibited (SSRF defense)")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFBlockedError(f"Could not resolve host '{hostname}': {e}") from e

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFBlockedError(f"Invalid resolved IP '{ip_str}'") from None

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SSRFBlockedError(
                f"Host '{hostname}' resolved to prohibited IP '{ip_str}' (SSRF defense)"
            )

        for blocked_net in BLOCKED_IP_NETWORKS:
            if ip in blocked_net:
                raise SSRFBlockedError(
                    f"Host '{hostname}' resolved to blocked network '{blocked_net}' (SSRF defense)"
                )


class SimpleHTMLInspector(HTMLParser):
    """Extract deterministic web signals and clean text from raw HTML."""

    def __init__(self):
        super().__init__()
        self.mobile_viewport = False
        self.has_contact_form = False
        self.has_booking_link = False
        self.social_links: set[str] = set()

        self._in_script_or_style = False
        self._in_form = False
        self._text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag in ("script", "style", "noscript"):
            self._in_script_or_style = True
            return

        if tag == "meta":
            name = attr_dict.get("name", "").lower()
            if name == "viewport":
                content = attr_dict.get("content", "").lower()
                if "width=" in content or "initial-scale=" in content:
                    self.mobile_viewport = True

        if tag == "form":
            self._in_form = True
            action = attr_dict.get("action", "").lower()
            form_id = attr_dict.get("id", "").lower()
            if "contact" in action or "contact" in form_id or "inquiry" in form_id:
                self.has_contact_form = True

        if self._in_form and tag in ("input", "textarea"):
            inp_type = attr_dict.get("type", "").lower()
            inp_name = attr_dict.get("name", "").lower()
            if (
                inp_type in ("email", "submit")
                or "email" in inp_name
                or "message" in inp_name
                or "phone" in inp_name
            ):
                self.has_contact_form = True

        if tag == "a":
            href = attr_dict.get("href", "").lower()
            # Booking detection
            booking_patterns = [
                "calendly.com",
                "opentable.com",
                "resy.com",
                "zocdoc.com",
                "book",
                "reserve",
                "appointment",
                "booking",
            ]
            if any(p in href for p in booking_patterns):
                self.has_booking_link = True

            # Social links detection
            social_domains = [
                "instagram.com",
                "facebook.com",
                "linkedin.com",
                "twitter.com",
                "x.com",
                "youtube.com",
            ]
            for domain in social_domains:
                if domain in href:
                    self.social_links.add(domain)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in ("script", "style", "noscript"):
            self._in_script_or_style = False
        elif tag == "form":
            self._in_form = False

    def handle_data(self, data: str):
        if not self._in_script_or_style:
            cleaned = data.strip()
            if cleaned:
                self._text_chunks.append(cleaned)

    def get_cleaned_text(self, max_length: int = 2000) -> str:
        full_text = " ".join(self._text_chunks)
        full_text = re.sub(r"\s+", " ", full_text).strip()
        return full_text[:max_length]


def fetch_website_safely(url: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> dict[str, Any]:
    """Safely fetch website homepage, compute deterministic signals, and extract clean text."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # SSRF verification on the initial URL
    validate_url_and_check_ssrf(url)

    start_time = time.time()
    https = url.lower().startswith("https://")

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    try:
        with (
            httpx.Client(timeout=timeout_sec, follow_redirects=True, max_redirects=3) as client,
            client.stream("GET", url, headers=headers) as response,
        ):
            # SSRF check on redirected target
            if str(response.url) != url:
                validate_url_and_check_ssrf(str(response.url))

            content_chunks = []
            total_bytes = 0

            for chunk in response.iter_bytes():
                total_bytes += len(chunk)
                if total_bytes > MAX_WEBSITE_BYTES:
                    logger.warning(
                        "Website %s exceeded max size limit of %d bytes",
                        url,
                        MAX_WEBSITE_BYTES,
                    )
                    break
                content_chunks.append(chunk)

            raw_bytes = b"".join(content_chunks)
            content_type = response.headers.get("content-type", "")
            encoding = "utf-8"
            if "charset=" in content_type.lower():
                try:
                    encoding = content_type.lower().split("charset=")[-1].split(";")[0].strip()
                except Exception:
                    encoding = "utf-8"

            html_text = raw_bytes.decode(encoding, errors="replace")

    except SSRFBlockedError:
        raise
    except Exception as e:
        logger.warning("Failed to safely fetch %s: %s", url, e)
        raise SafeFetcherError(f"HTTP fetch failed for {url}: {e}") from e

    load_time_ms = round((time.time() - start_time) * 1000, 1)

    inspector = SimpleHTMLInspector()
    inspector.feed(html_text)

    cleaned_text = inspector.get_cleaned_text()

    return {
        "url": url,
        "https": https,
        "load_time_ms": load_time_ms,
        "mobile_viewport": inspector.mobile_viewport,
        "has_contact_form": inspector.has_contact_form,
        "has_booking_link": inspector.has_booking_link,
        "social_links": sorted(inspector.social_links),
        "cleaned_text": cleaned_text,
    }
