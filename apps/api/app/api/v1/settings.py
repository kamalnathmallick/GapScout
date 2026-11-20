"""Settings, Workspace Caps, Scoring Weights, and API Usage endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import LLMUsageLog, OfferProfile, Workspace
from app.schemas.settings import (
    ApiUsageOut,
    ScoringWeightsOut,
    ScoringWeightsUpdate,
    WorkspaceCapsOut,
    WorkspaceCapsUpdate,
)
from app.scoring.config import ScoringWeights

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_WEIGHTS_DICT = ScoringWeights().model_dump()


@router.get("/workspace-caps", response_model=WorkspaceCapsOut)
def get_workspace_caps(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
) -> WorkspaceCapsOut:
    """Get current workspace execution caps and data retention configuration."""
    return WorkspaceCapsOut(
        max_cells_per_job=workspace.max_cells_per_job,
        max_places_per_job=workspace.max_places_per_job,
        daily_llm_cost_cap_usd=workspace.daily_llm_cost_cap_usd,
        data_retention_days=workspace.data_retention_days,
    )


@router.put("/workspace-caps", response_model=WorkspaceCapsOut)
def update_workspace_caps(
    payload: WorkspaceCapsUpdate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceCapsOut:
    """Update workspace execution caps and data retention policy."""
    if payload.max_cells_per_job is not None:
        workspace.max_cells_per_job = payload.max_cells_per_job
    if payload.max_places_per_job is not None:
        workspace.max_places_per_job = payload.max_places_per_job
    if payload.daily_llm_cost_cap_usd is not None:
        workspace.daily_llm_cost_cap_usd = payload.daily_llm_cost_cap_usd
    if payload.data_retention_days is not None:
        workspace.data_retention_days = payload.data_retention_days

    db.commit()
    db.refresh(workspace)

    return WorkspaceCapsOut(
        max_cells_per_job=workspace.max_cells_per_job,
        max_places_per_job=workspace.max_places_per_job,
        daily_llm_cost_cap_usd=workspace.daily_llm_cost_cap_usd,
        data_retention_days=workspace.data_retention_days,
    )


@router.get("/scoring-weights", response_model=ScoringWeightsOut)
def get_scoring_weights(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ScoringWeightsOut:
    """Get active lead scoring weights for workspace."""
    profile = db.scalar(select(OfferProfile).where(OfferProfile.workspace_id == workspace.id))
    weights = profile.weights if (profile and profile.weights) else DEFAULT_WEIGHTS_DICT
    is_custom = bool(profile and profile.weights and profile.weights != DEFAULT_WEIGHTS_DICT)

    return ScoringWeightsOut(weights=weights, is_custom=is_custom)


@router.put("/scoring-weights", response_model=ScoringWeightsOut)
def update_scoring_weights(
    payload: ScoringWeightsUpdate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ScoringWeightsOut:
    """Update workspace custom scoring weights."""
    profile = db.scalar(select(OfferProfile).where(OfferProfile.workspace_id == workspace.id))
    if not profile:
        profile = OfferProfile(workspace_id=workspace.id, weights=payload.weights)
        db.add(profile)
    else:
        profile.weights = payload.weights

    db.commit()
    db.refresh(profile)

    return ScoringWeightsOut(weights=profile.weights, is_custom=True)


@router.post("/scoring-weights/reset", response_model=ScoringWeightsOut)
def reset_scoring_weights(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ScoringWeightsOut:
    """Reset workspace scoring weights back to factory default values."""
    profile = db.scalar(select(OfferProfile).where(OfferProfile.workspace_id == workspace.id))
    if profile:
        profile.weights = DEFAULT_WEIGHTS_DICT
        db.commit()
        db.refresh(profile)

    return ScoringWeightsOut(weights=DEFAULT_WEIGHTS_DICT, is_custom=False)


@router.get("/api-usage", response_model=ApiUsageOut)
def get_api_usage(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ApiUsageOut:
    """Get LLM API usage breakdown and daily budget tracking."""
    # Aggregated all-time stats
    stmt_all = select(
        func.count(LLMUsageLog.id),
        func.coalesce(func.sum(LLMUsageLog.prompt_tokens), 0),
        func.coalesce(func.sum(LLMUsageLog.completion_tokens), 0),
        func.coalesce(func.sum(LLMUsageLog.cost_usd), 0.0),
    ).where(LLMUsageLog.workspace_id == workspace.id)

    row_all = db.execute(stmt_all).one()
    total_calls, prompt_tokens, completion_tokens, total_cost = row_all

    # Today's cost
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt_today = select(func.coalesce(func.sum(LLMUsageLog.cost_usd), 0.0)).where(
        LLMUsageLog.workspace_id == workspace.id,
        LLMUsageLog.created_at >= today_start,
    )
    cost_today = float(db.scalar(stmt_today) or 0.0)

    daily_cap = float(workspace.daily_llm_cost_cap_usd)
    remaining_budget = max(0.0, daily_cap - cost_today)

    return ApiUsageOut(
        total_calls=int(total_calls),
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_cost_usd=round(float(total_cost), 4),
        cost_today_usd=round(cost_today, 4),
        daily_cost_cap_usd=round(daily_cap, 2),
        remaining_budget_today_usd=round(remaining_budget, 4),
    )
