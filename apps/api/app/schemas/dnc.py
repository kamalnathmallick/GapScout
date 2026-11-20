"""Do-Not-Contact schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DNCRequest(BaseModel):
    email: str | None = None
    domain: str | None = None
    phone: str | None = None
    reason: str | None = Field(default=None, description="Reason for adding to DNC list")


class DNCOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str | None = None
    domain: str | None = None
    phone: str | None = None
    reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DNCListOut(BaseModel):
    items: list[DNCOut]
    total: int
