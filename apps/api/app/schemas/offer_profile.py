"""Pydantic schemas for workspace Offer Profiles."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OfferProfileBase(BaseModel):
    name: str = Field(default="Default Offer", max_length=120)
    offer_description: str | None = Field(default=None)
    target_categories: list[str] = Field(default_factory=list)
    min_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    max_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    target_regions: list[str] = Field(default_factory=list)
    weights: dict[str, Any] = Field(default_factory=dict)


class OfferProfileCreate(OfferProfileBase):
    pass


class OfferProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    offer_description: str | None = None
    target_categories: list[str] | None = None
    min_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    max_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    target_regions: list[str] | None = None
    weights: dict[str, Any] | None = None


class OfferProfileOut(OfferProfileBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
