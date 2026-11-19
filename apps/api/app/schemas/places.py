"""Place schemas and filters."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class PlaceOut(BaseModel):
    """Place response schema."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    category: str | None
    normalized_category: str | None
    address: str | None
    phone_e164: str | None
    website: str | None
    website_domain: str | None
    email: str | None
    rating: float | None
    review_count: int
    price_level: int | None
    h3_r8: str | None
    is_closed: bool
    latitude: float | None = None
    longitude: float | None = None
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class PlacesListOut(BaseModel):
    """Paginated list of places."""

    items: list[PlaceOut]
    pagination: PaginationMeta
