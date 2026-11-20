"""Offer Profile management endpoints for workspace targeting and lead fit scoring."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import OfferProfile, Workspace
from app.schemas.offer_profile import OfferProfileOut, OfferProfileUpdate
from app.scoring.pipeline import score_workspace_leads

router = APIRouter(prefix="/offer-profile", tags=["offer-profile"])


@router.get("", response_model=OfferProfileOut)
def get_offer_profile(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> OfferProfileOut:
    """Get the current workspace Offer Profile (or create default if none exists)."""
    profile = db.execute(
        select(OfferProfile).where(OfferProfile.workspace_id == workspace.id)
    ).scalar_one_or_none()

    if not profile:
        profile = OfferProfile(
            workspace_id=workspace.id,
            name="Default Offer",
            offer_description="",
            target_categories=[],
            min_rating=None,
            max_rating=None,
            target_regions=[],
            weights={},
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return OfferProfileOut.model_validate(profile)


@router.patch("", response_model=OfferProfileOut, status_code=status.HTTP_200_OK)
@router.put("", response_model=OfferProfileOut, status_code=status.HTTP_200_OK)
def update_offer_profile(
    payload: OfferProfileUpdate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    rescore_leads: bool = True,
) -> OfferProfileOut:
    """Update workspace Offer Profile and automatically re-score workspace leads."""
    profile = db.execute(
        select(OfferProfile).where(OfferProfile.workspace_id == workspace.id)
    ).scalar_one_or_none()

    if not profile:
        profile = OfferProfile(workspace_id=workspace.id)
        db.add(profile)

    if payload.name is not None:
        profile.name = payload.name
    if payload.offer_description is not None:
        profile.offer_description = payload.offer_description
    if payload.target_categories is not None:
        profile.target_categories = payload.target_categories
    if payload.min_rating is not None:
        profile.min_rating = payload.min_rating
    if payload.max_rating is not None:
        profile.max_rating = payload.max_rating
    if payload.target_regions is not None:
        profile.target_regions = payload.target_regions
    if payload.weights is not None:
        profile.weights = payload.weights

    db.commit()
    db.refresh(profile)

    if rescore_leads:
        score_workspace_leads(db, workspace.id)

    return OfferProfileOut.model_validate(profile)
