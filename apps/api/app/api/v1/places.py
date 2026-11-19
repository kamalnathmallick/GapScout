"""Places endpoints with filtering and pagination."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import Place, Workspace
from app.schemas.common import PaginationMeta
from app.schemas.places import PlaceOut, PlacesListOut

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=PlacesListOut)
def list_places(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    category: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=1.0, le=5.0),
    has_website: bool | None = Query(default=None),
    hex: str | None = Query(default=None, description="Filter by H3 resolution 8 index"),
    search: str | None = Query(default=None, description="Text search in place name or address"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PlacesListOut:
    """List places in workspace with filters and pagination."""
    query = select(Place).where(Place.workspace_id == workspace.id)

    if category:
        cat_lower = category.strip().lower()
        query = query.where(
            (func.lower(Place.normalized_category) == cat_lower)
            | (func.lower(Place.category) == cat_lower)
        )

    if min_rating is not None:
        query = query.where(Place.rating >= min_rating)

    if has_website is not None:
        if has_website:
            query = query.where(Place.website.is_not(None))
        else:
            query = query.where(Place.website.is_(None))

    if hex:
        query = query.where(Place.h3_r8 == hex.strip())

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Place.name).ilike(search_pattern)
            | func.lower(Place.address).ilike(search_pattern)
        )

    # Count total matching
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Paginate
    query = query.order_by(Place.rating.desc().nullslast(), Place.name.asc())
    query = query.limit(limit).offset(offset)

    places = db.scalars(query).all()

    items = []
    for p in places:
        lat, lon = None, None
        if p.location is not None:
            try:
                pt = to_shape(p.location)
                lat, lon = float(pt.y), float(pt.x)
            except Exception:
                pass
        if lat is None and isinstance(p.raw, dict):
            lat = p.raw.get("latitude") or p.raw.get("lat")
            lon = p.raw.get("longitude") or p.raw.get("lng")

        items.append(
            PlaceOut(
                id=p.id,
                workspace_id=p.workspace_id,
                name=p.name,
                category=p.category,
                normalized_category=p.normalized_category,
                address=p.address,
                phone_e164=p.phone_e164,
                website=p.website,
                website_domain=p.website_domain,
                email=p.email,
                rating=p.rating,
                review_count=p.review_count,
                price_level=p.price_level,
                h3_r8=p.h3_r8,
                is_closed=p.is_closed,
                latitude=float(lat) if lat is not None else None,
                longitude=float(lon) if lon is not None else None,
                first_seen_at=p.first_seen_at,
                last_seen_at=p.last_seen_at,
            )
        )

    return PlacesListOut(
        items=items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total,
        ),
    )
