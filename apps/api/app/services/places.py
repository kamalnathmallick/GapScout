"""Place persistence and upsert services."""

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Place, PlaceReview
from app.providers.base import PlaceDTO

logger = logging.getLogger(__name__)


def upsert_places(
    db: Session,
    workspace_id: uuid.UUID,
    places_dto: Sequence[PlaceDTO],
) -> list[uuid.UUID]:
    """Upsert a sequence of PlaceDTO objects into the places table.

    Keyed by (workspace_id, provider, provider_place_id). Re-running never duplicates rows.
    Untouched provider record is stored in places.raw. Associated reviews are stored
    in place_reviews.

    Returns the list of affected place UUIDs.
    """
    if not places_dto:
        return []

    place_ids: list[uuid.UUID] = []

    for dto in places_dto:
        location = None
        if dto.latitude is not None and dto.longitude is not None:
            location = WKTElement(f"POINT({dto.longitude} {dto.latitude})", srid=4326)

        stmt = insert(Place).values(
            workspace_id=workspace_id,
            provider=dto.provider,
            provider_place_id=dto.provider_place_id,
            name=dto.name,
            category=dto.category,
            address=dto.address,
            phone_e164=dto.phone,
            website=dto.website,
            email=dto.email,
            rating=dto.rating,
            review_count=dto.review_count,
            price_level=dto.price_level,
            location=location,
            opening_hours=dto.opening_hours,
            is_closed=dto.is_closed,
            raw=dto.raw,
            last_seen_at=func.now(),
        )

        upsert_stmt = stmt.on_conflict_do_update(
            constraint="uq_places_provider_place",
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "address": stmt.excluded.address,
                "phone_e164": stmt.excluded.phone_e164,
                "website": stmt.excluded.website,
                "email": stmt.excluded.email,
                "rating": stmt.excluded.rating,
                "review_count": stmt.excluded.review_count,
                "price_level": stmt.excluded.price_level,
                "location": stmt.excluded.location,
                "opening_hours": stmt.excluded.opening_hours,
                "is_closed": stmt.excluded.is_closed,
                "raw": stmt.excluded.raw,
                "last_seen_at": func.now(),
            },
        ).returning(Place.id)

        place_id = db.execute(upsert_stmt).scalar_one()
        place_ids.append(place_id)

        # Upsert or save reviews if present
        if dto.reviews:
            # Delete prior reviews for this place to refresh with latest scraped reviews
            db.query(PlaceReview).filter(
                PlaceReview.workspace_id == workspace_id,
                PlaceReview.place_id == place_id,
            ).delete()

            seen_reviews: set[tuple[str | None, datetime | None]] = set()
            review_objects: list[PlaceReview] = []
            for rev in dto.reviews:
                key = (rev.text, rev.published_at)
                if key in seen_reviews:
                    continue
                seen_reviews.add(key)
                review_objects.append(
                    PlaceReview(
                        workspace_id=workspace_id,
                        place_id=place_id,
                        rating=rev.rating,
                        review_text=rev.text,
                        published_at=rev.published_at,
                        owner_replied=rev.owner_replied,
                    )
                )

            if review_objects:
                db.add_all(review_objects)

    db.commit()
    logger.info("Upserted %d places for workspace %s", len(place_ids), workspace_id)
    return place_ids
