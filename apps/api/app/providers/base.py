"""Abstract DataSourceProvider interface and data models."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawPlace(BaseModel):
    """Untouched place data returned by an upstream provider."""

    provider: str
    provider_place_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class ReviewDTO(BaseModel):
    """Normalized review data."""

    author_name: str | None = None
    rating: int | None = None
    text: str | None = None
    published_at: datetime | None = None
    owner_replied: bool = False


class PlaceDTO(BaseModel):
    """Normalized place ready for persistence in PostgreSQL/PostGIS."""

    provider: str
    provider_place_id: str
    name: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    rating: float | None = None
    review_count: int = 0
    price_level: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    opening_hours: dict[str, Any] | None = None
    is_closed: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)
    reviews: list[ReviewDTO] = Field(default_factory=list)


class SearchOptions(BaseModel):
    """Configurable options for data source queries."""

    lat: float | None = None
    lon: float | None = None
    radius: int = 5000
    zoom: int = 15
    depth: int = 1
    email: bool = True
    lang: str = "en"
    max_time: int = 300
    proxies: list[str] = Field(default_factory=list)


class DataSourceProvider(ABC):
    """Abstract interface that every place data provider must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the data source provider."""
        ...

    @abstractmethod
    def search(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[RawPlace]:
        """Query the upstream data source for places matching category and area."""
        ...

    @abstractmethod
    def to_place_dto(self, raw: RawPlace) -> PlaceDTO:
        """Map a raw provider record to a normalized PlaceDTO."""
        ...

    def search_and_map(
        self,
        category: str,
        area_or_cell: str,
        options: SearchOptions | None = None,
    ) -> list[PlaceDTO]:
        """Convenience method to query and map places in a single call."""
        raw_places = self.search(category, area_or_cell, options)
        return [self.to_place_dto(rp) for rp in raw_places]
