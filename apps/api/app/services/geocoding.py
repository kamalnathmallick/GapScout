"""Geocoding service using OpenStreetMap Nominatim with caching and polite user agent."""

import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


class BoundingBox(BaseModel):
    """Geographic bounding box defined by WGS84 coordinates."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    display_name: str | None = None

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2.0

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2.0

    def to_wkt_polygon(self) -> str:
        """Export as EWKT polygon string for PostGIS."""
        # Closed polygon: min_lon min_lat -> max_lon min_lat ->
        # max_lon max_lat -> min_lon max_lat -> min_lon min_lat
        return (
            f"SRID=4326;POLYGON(("
            f"{self.min_lon} {self.min_lat}, "
            f"{self.max_lon} {self.min_lat}, "
            f"{self.max_lon} {self.max_lat}, "
            f"{self.min_lon} {self.max_lat}, "
            f"{self.min_lon} {self.min_lat}))"
        )


class GeocodingError(Exception):
    """Raised when geocoding fails or location is not found."""


# In-memory query cache: query -> BoundingBox
_GEOCODE_CACHE: dict[str, BoundingBox] = {}


def geocode_area(
    area_name: str,
    client: httpx.Client | None = None,
    user_agent: str | None = None,
) -> BoundingBox:
    """Geocode an area or city name to a BoundingBox using Nominatim.

    Caches results in memory to avoid repeated external requests.
    """
    normalized_query = area_name.strip().lower()
    if normalized_query in _GEOCODE_CACHE:
        logger.debug("Geocode cache hit for: %s", area_name)
        return _GEOCODE_CACHE[normalized_query]

    settings = get_settings()
    ua = user_agent or settings.geocoder_user_agent
    headers = {"User-Agent": ua}
    params: dict[str, str | int] = {
        "q": area_name,
        "format": "json",
        "limit": 1,
    }

    url = "https://nominatim.openstreetmap.org/search"
    logger.info("Geocoding area '%s' via %s (User-Agent: %s)", area_name, url, ua)

    http_client = client or httpx.Client(timeout=10.0)
    try:
        resp = http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        results: list[dict[str, Any]] = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Nominatim request error for '%s': %s", area_name, exc)
        raise GeocodingError(f"Nominatim request failed: {exc}") from exc

    if not results:
        raise GeocodingError(f"Could not find coordinates for area: '{area_name}'")

    top = results[0]
    bbox_raw = top.get("boundingbox")
    if not bbox_raw or len(bbox_raw) < 4:
        raise GeocodingError(f"Nominatim did not return a valid boundingbox for: '{area_name}'")

    # Nominatim format: [south_lat, north_lat, west_lon, east_lon]
    bbox = BoundingBox(
        min_lat=float(bbox_raw[0]),
        max_lat=float(bbox_raw[1]),
        min_lon=float(bbox_raw[2]),
        max_lon=float(bbox_raw[3]),
        display_name=top.get("display_name"),
    )

    _GEOCODE_CACHE[normalized_query] = bbox
    return bbox
