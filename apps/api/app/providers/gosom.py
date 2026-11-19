"""Gosom Google Maps Scraper provider implementation."""

import csv
import io
import json
import logging
import re
import time
from datetime import datetime
from typing import Any

import httpx

from app.providers.base import DataSourceProvider, PlaceDTO, RawPlace, ReviewDTO, SearchOptions

logger = logging.getLogger(__name__)


class GosomScraperError(Exception):
    """Raised when communication with the scraper service fails."""


class GosomTimeoutError(GosomScraperError):
    """Raised when job polling times out."""


class GosomScraperProvider(DataSourceProvider):
    """Data source provider that drives the gosom/google-maps-scraper REST API."""

    def __init__(
        self,
        base_url: str = "http://scraper:8080",
        client: httpx.Client | None = None,
        timeout: float = 300.0,
        initial_poll_interval: float = 1.0,
        max_poll_interval: float = 5.0,
        backoff_factor: float = 1.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client
        self.timeout = timeout
        self.initial_poll_interval = initial_poll_interval
        self.max_poll_interval = max_poll_interval
        self.backoff_factor = backoff_factor

    @property
    def name(self) -> str:
        return "gosom"

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=30.0)

    def search(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[RawPlace]:
        """Submit a scrape job, poll for completion, and return raw place records."""
        opts = options or SearchOptions()
        query = f"{category} in {area_or_cell}".strip()
        job_id = self.create_job(query=query, options=opts)
        self.poll_until_complete(job_id=job_id)
        csv_text = self.download_results(job_id=job_id)
        return self.parse_csv_to_raw_places(csv_text)

    def create_job(self, query: str, options: SearchOptions) -> str:
        """Create a new scraping job via POST /api/v1/jobs."""
        payload: dict[str, Any] = {
            "name": f"GapScout: {query}",
            "keywords": [query],
            "lang": options.lang,
            "zoom": options.zoom,
            "depth": options.depth,
            "email": options.email,
            "max_time": options.max_time,
        }
        if options.lat is not None and options.lon is not None:
            payload["lat"] = str(options.lat)
            payload["lon"] = str(options.lon)
            payload["radius"] = options.radius
        if options.proxies:
            payload["proxies"] = options.proxies

        # Never log sensitive proxy credentials
        clean_log_payload = {k: v for k, v in payload.items() if k != "proxies"}
        logger.info("Submitting scrape job to %s/api/v1/jobs: %s", self.base_url, clean_log_payload)

        client = self._get_client()
        try:
            resp = client.post(f"{self.base_url}/api/v1/jobs", json=payload)
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("id") or data.get("ID")
            if not job_id:
                raise GosomScraperError(f"Scraper returned 201 but no job id: {data}")
            logger.info("Scraper job created with ID: %s", job_id)
            return str(job_id)
        except httpx.HTTPError as exc:
            logger.error("Failed to create scraper job: %s", exc)
            raise GosomScraperError(f"Failed to create scraper job: {exc}") from exc

    def poll_until_complete(self, job_id: str) -> dict[str, Any]:
        """Poll GET /api/v1/jobs/{id} with exponential backoff until completed or failed."""
        start_time = time.time()
        interval = self.initial_poll_interval
        client = self._get_client()

        logger.info("Polling job %s with timeout %.1fs", job_id, self.timeout)

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise GosomTimeoutError(
                    f"Job {job_id} did not finish within timeout of {self.timeout}s "
                    f"(elapsed: {elapsed:.1f}s)"
                )

            try:
                resp = client.get(f"{self.base_url}/api/v1/jobs/{job_id}")
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                logger.warning("Transient error polling job %s: %s", job_id, exc)
                time.sleep(interval)
                interval = min(interval * self.backoff_factor, self.max_poll_interval)
                continue

            status = str(data.get("status") or data.get("Status") or "").lower()
            logger.debug("Job %s status: %s (elapsed %.1fs)", job_id, status, elapsed)

            if status in ("ok", "completed", "done", "finished", "success"):
                logger.info("Job %s completed successfully in %.1fs", job_id, elapsed)
                return data
            elif status in ("failed", "error", "cancelled"):
                raise GosomScraperError(f"Job {job_id} terminated with failure status: {status}")

            time.sleep(interval)
            interval = min(interval * self.backoff_factor, self.max_poll_interval)

    def download_results(self, job_id: str) -> str:
        """Download CSV results for a finished job via GET /api/v1/jobs/{id}/download."""
        client = self._get_client()
        logger.info("Downloading results for job %s from %s", job_id, self.base_url)
        try:
            resp = client.get(f"{self.base_url}/api/v1/jobs/{job_id}/download")
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as exc:
            logger.error("Failed to download results for job %s: %s", job_id, exc)
            raise GosomScraperError(f"Failed to download job results: {exc}") from exc

    def parse_csv_to_raw_places(self, csv_content: str) -> list[RawPlace]:
        """Parse raw CSV string into a list of RawPlace objects."""
        if not csv_content.strip():
            return []

        # Strip null bytes and normalize line endings
        sanitized = csv_content.replace("\x00", "")
        reader = csv.DictReader(io.StringIO(sanitized))
        raw_places: list[RawPlace] = []

        for row in reader:
            provider_place_id = (
                row.get("place_id") or row.get("cid") or row.get("data_id") or row.get("link") or ""
            ).strip()
            if not provider_place_id:
                # If identifier is missing, hash name and address for a deterministic fallback
                name = row.get("title") or "unknown"
                address = row.get("address") or ""
                provider_place_id = f"fallback_{hash(f'{name}:{address}')}"

            raw_places.append(
                RawPlace(
                    provider=self.name,
                    provider_place_id=provider_place_id,
                    data=dict(row),
                )
            )

        return raw_places

    def to_place_dto(self, raw: RawPlace) -> PlaceDTO:
        """Map a RawPlace dictionary into a validated PlaceDTO."""
        d = raw.data

        # Name
        name = str(d.get("title") or d.get("name") or "Unnamed Place").strip()

        # Categories
        category = d.get("category")
        if category:
            category = str(category).strip() or None

        # Address & Contact
        address = d.get("address")
        if address:
            address = str(address).strip() or None

        phone = d.get("phone")
        if phone:
            phone = str(phone).strip() or None

        website = d.get("website")
        if website:
            website = str(website).strip() or None

        # Email extraction: either from 'emails' (JSON list or string) or 'email'
        email = self._extract_email(d)

        # Rating and review count
        rating = self._parse_float(d.get("review_rating"))
        review_count = self._parse_int(d.get("review_count"), default=0)

        # Price level
        price_level = self._parse_price_level(d.get("price_range"))

        # Coordinates
        latitude = self._parse_float(d.get("latitude"))
        longitude = self._parse_float(d.get("longitude"))

        # Opening hours
        opening_hours = self._parse_json_dict(d.get("open_hours"))

        # Operational status
        status_text = str(d.get("status") or "").lower()
        is_closed = "closed" in status_text or "permanently closed" in status_text

        # Reviews
        reviews = self._extract_reviews(d.get("user_reviews"))

        return PlaceDTO(
            provider=raw.provider,
            provider_place_id=raw.provider_place_id,
            name=name,
            category=category,
            address=address,
            phone=phone,
            website=website,
            email=email,
            rating=rating,
            review_count=review_count,
            price_level=price_level,
            latitude=latitude,
            longitude=longitude,
            opening_hours=opening_hours,
            is_closed=is_closed,
            raw=d,
            reviews=reviews,
        )

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_int(val: Any, default: int = 0) -> int:
        if val is None or val == "":
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_price_level(val: Any) -> int | None:
        if not val:
            return None
        s = str(val).strip()
        if s.isdigit():
            return int(s)
        # Currency symbols: $, ₹, €, £
        match = re.search(r"[$₹€£]+", s)
        if match:
            return len(match.group(0))
        return None

    @staticmethod
    def _parse_json_dict(val: Any) -> dict[str, Any] | None:
        if not val or not isinstance(val, str):
            return None if not isinstance(val, dict) else val
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _extract_email(data: dict[str, Any]) -> str | None:
        raw_emails = data.get("emails") or data.get("email")
        if not raw_emails:
            return None
        if isinstance(raw_emails, list) and raw_emails:
            return str(raw_emails[0]).strip() or None
        if isinstance(raw_emails, str):
            s = raw_emails.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    lst = json.loads(s)
                    if isinstance(lst, list) and lst:
                        return str(lst[0]).strip() or None
                except (json.JSONDecodeError, TypeError):
                    pass
            # Comma-separated or single email
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return parts[0] if parts else None
        return None

    @classmethod
    def _extract_reviews(cls, raw_reviews: Any) -> list[ReviewDTO]:
        if not raw_reviews:
            return []
        items: list[Any] = []
        if isinstance(raw_reviews, list):
            items = raw_reviews
        elif isinstance(raw_reviews, str):
            s = raw_reviews.strip()
            if not s or s in ("null", "None", "[]"):
                return []
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    items = parsed
            except (json.JSONDecodeError, TypeError):
                logger.debug("Failed to parse reviews JSON defensively: %s", s[:80])
                return []

        reviews: list[ReviewDTO] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            author_name = str(item.get("Name") or item.get("author_name") or "").strip() or None
            rating_val = cls._parse_int(item.get("Rating") or item.get("rating"))
            rating = rating_val if rating_val > 0 else None
            text_val = (
                str(
                    item.get("Description") or item.get("text_original") or item.get("text") or ""
                ).strip()
                or None
            )

            pub_at: datetime | None = None
            pub_raw = item.get("published_at")
            if pub_raw and isinstance(pub_raw, str):
                try:
                    # Parse standard ISO string like '2026-10-14T11:22:35.07145Z'
                    clean_ts = pub_raw.rstrip("Z")
                    pub_at = datetime.fromisoformat(clean_ts)
                except ValueError:
                    pub_at = None

            # Detect owner response
            owner_reply = bool(
                item.get("reply_text_original")
                or item.get("owner_reply")
                or item.get("owner_replied")
            )

            reviews.append(
                ReviewDTO(
                    author_name=author_name,
                    rating=rating,
                    text=text_val,
                    published_at=pub_at,
                    owner_replied=owner_reply,
                )
            )

        return reviews
