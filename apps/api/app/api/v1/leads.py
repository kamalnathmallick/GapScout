"""Leads, outreach drafts, and events endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import Lead, OutreachDraft, OutreachEvent, Place, Workspace
from app.schemas.common import PaginationMeta
from app.schemas.leads import (
    LeadOut,
    LeadsListOut,
    LeadUpdateRequest,
    OutreachDraftOut,
    OutreachDraftRequest,
    OutreachEventOut,
    OutreachEventRequest,
)
from app.schemas.places import PlaceOut

router = APIRouter(prefix="/leads", tags=["leads"])

ALLOWED_STATUSES = {
    "new",
    "shortlisted",
    "contacted",
    "replied",
    "meeting",
    "converted",
    "rejected",
    "do_not_contact",
}


def _place_to_place_out(p: Place | None) -> PlaceOut | None:
    if not p:
        return None
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

    return PlaceOut(
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


def _build_lead_out(
    lead: Lead,
    place: Place | None = None,
    drafts: list[OutreachDraft] | None = None,
    events: list[OutreachEvent] | None = None,
) -> LeadOut:
    return LeadOut(
        id=lead.id,
        workspace_id=lead.workspace_id,
        place_id=lead.place_id,
        status=lead.status,
        rule_score=lead.rule_score,
        ml_score=lead.ml_score,
        final_score=lead.final_score,
        score_breakdown=lead.score_breakdown,
        notes=lead.notes,
        place=_place_to_place_out(place),
        drafts=[OutreachDraftOut.model_validate(d) for d in (drafts or [])],
        events=[OutreachEventOut.model_validate(e) for e in (events or [])],
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("", response_model=LeadsListOut)
def list_leads(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
    min_score: float | None = Query(default=None, ge=0.0, le=100.0),
    has_email: bool | None = Query(default=None),
    hex: str | None = Query(default=None, description="H3 index"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> LeadsListOut:
    """List leads with filtering and final_score sorting."""
    query = (
        select(Lead, Place)
        .join(Place, Place.id == Lead.place_id)
        .where(Lead.workspace_id == workspace.id)
    )

    if status:
        query = query.where(Lead.status == status.strip().lower())

    if min_score is not None:
        query = query.where(Lead.final_score >= min_score)

    if has_email is not None:
        if has_email:
            query = query.where(Place.email.is_not(None))
        else:
            query = query.where(Place.email.is_(None))

    if hex:
        query = query.where(Place.h3_r8 == hex.strip())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    query = query.order_by(Lead.final_score.desc().nullslast(), Lead.created_at.desc())
    query = query.limit(limit).offset(offset)

    results = db.execute(query).all()
    items = [_build_lead_out(lead=row[0], place=row[1]) for row in results]

    return LeadsListOut(
        items=items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total,
        ),
    )


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadOut:
    """Get single lead details with place information, drafts, and events."""
    lead = db.get(Lead, lead_id)
    if not lead or lead.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    place = db.get(Place, lead.place_id)
    drafts = list(
        db.scalars(
            select(OutreachDraft)
            .where(OutreachDraft.lead_id == lead.id)
            .order_by(OutreachDraft.created_at.desc())
        ).all()
    )
    events = list(
        db.scalars(
            select(OutreachEvent)
            .where(OutreachEvent.lead_id == lead.id)
            .order_by(OutreachEvent.occurred_at.desc())
        ).all()
    )

    return _build_lead_out(lead=lead, place=place, drafts=drafts, events=events)


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: uuid.UUID,
    req: LeadUpdateRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadOut:
    """Update lead status or internal notes."""
    lead = db.get(Lead, lead_id)
    if not lead or lead.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    if req.status is not None:
        st_clean = req.status.strip().lower()
        if st_clean not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{req.status}'. Allowed: {sorted(ALLOWED_STATUSES)}",
            )
        lead.status = st_clean

    if req.notes is not None:
        lead.notes = req.notes

    db.commit()
    db.refresh(lead)

    place = db.get(Place, lead.place_id)
    return _build_lead_out(lead=lead, place=place)


@router.post(
    "/{lead_id}/drafts",
    response_model=OutreachDraftOut,
    status_code=status.HTTP_201_CREATED,
)
def create_lead_draft(
    lead_id: uuid.UUID,
    req: OutreachDraftRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> OutreachDraftOut:
    """Create and record an outreach draft for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead or lead.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    channel = req.channel.strip().lower()
    if channel not in {"email", "chat"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel must be 'email' or 'chat'.",
        )

    draft = OutreachDraft(
        workspace_id=workspace.id,
        lead_id=lead.id,
        channel=channel,
        body=req.body.strip(),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return OutreachDraftOut.model_validate(draft)


@router.post(
    "/{lead_id}/events",
    response_model=OutreachEventOut,
    status_code=status.HTTP_201_CREATED,
)
def create_lead_event(
    lead_id: uuid.UUID,
    req: OutreachEventRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> OutreachEventOut:
    """Record an outreach event (e.g. 'contacted', 'replied')."""
    lead = db.get(Lead, lead_id)
    if not lead or lead.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    event = OutreachEvent(
        workspace_id=workspace.id,
        lead_id=lead.id,
        event_type=req.event_type.strip().lower(),
        features_snapshot=req.features_snapshot,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return OutreachEventOut.model_validate(event)
