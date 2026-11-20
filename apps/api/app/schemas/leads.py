"""Lead, outreach draft, and outreach event schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta
from app.schemas.places import PlaceOut


class LeadUpdateRequest(BaseModel):
    """Update lead status or internal notes."""

    status: str | None = Field(
        default=None,
        description="Allowed: new, shortlisted, contacted, replied, meeting, converted, rejected",
    )
    notes: str | None = None


class OutreachDraftRequest(BaseModel):
    """Create a new outreach draft."""

    channel: str = Field(description="'email' or 'chat'")
    body: str = Field(min_length=5, description="Draft message text")


class OutreachDraftOut(BaseModel):
    """Outreach draft details."""

    id: uuid.UUID
    lead_id: uuid.UUID
    channel: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateDraftRequest(BaseModel):
    """Parameters for AI / grounded outreach draft generation."""

    channel: str = Field(default="email", description="'email' or 'chat'")
    tone: str = Field(default="direct", description="'direct', 'consultative', or 'casual'")
    custom_offer: str | None = None


class GeneratedDraftOut(BaseModel):
    """Generated draft with grounded constraints and direct open links."""

    id: uuid.UUID
    lead_id: uuid.UUID
    channel: str
    body: str
    word_count: int
    char_count: int
    mailto_link: str | None = None
    wa_link: str | None = None
    created_at: datetime



class OutreachEventRequest(BaseModel):
    """Record an outreach event (e.g. contacted, replied)."""

    event_type: str = Field(description="e.g. 'contacted', 'replied', 'meeting_booked'")
    features_snapshot: dict[str, Any] | None = None


class OutreachEventOut(BaseModel):
    """Recorded outreach event."""

    id: uuid.UUID
    lead_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    features_snapshot: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class LeadOut(BaseModel):
    """Lead details."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    place_id: uuid.UUID
    status: str
    rule_score: float | None
    ml_score: float | None
    final_score: float | None
    score_breakdown: dict[str, Any]
    notes: str | None
    place: PlaceOut | None = None
    drafts: list[OutreachDraftOut] = []
    events: list[OutreachEventOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadsListOut(BaseModel):
    """Paginated list of leads."""

    items: list[LeadOut]
    pagination: PaginationMeta
