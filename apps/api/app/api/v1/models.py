"""Model version and training endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.models import ModelVersion, Workspace
from app.outcomes.dataset import build_training_dataset, get_dataset_health
from app.schemas.models import (
    ActiveModelMetricsOut,
    ModelTrainRequest,
    ModelVersionOut,
)
from app.schemas.outcomes import DatasetHealthOut

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelVersionOut])
def list_models(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ModelVersionOut]:
    """List trained model versions for current workspace."""
    stmt = (
        select(ModelVersion)
        .where(ModelVersion.workspace_id == workspace.id)
        .order_by(ModelVersion.trained_at.desc())
    )
    models = list(db.scalars(stmt).all())
    return [
        ModelVersionOut(
            id=m.id,
            workspace_id=m.workspace_id,
            algorithm=m.algorithm,
            trained_at=m.trained_at,
            n_samples=m.n_samples,
            metrics=m.metrics,
            feature_list=[str(f) for f in m.feature_list],
            is_active=m.is_active,
        )
        for m in models
    ]


@router.get("/active/metrics", response_model=ActiveModelMetricsOut)
def get_active_model_metrics(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ActiveModelMetricsOut:
    """Get active model evaluation metrics or cold-start fallback status."""
    stmt = select(ModelVersion).where(
        ModelVersion.workspace_id == workspace.id,
        ModelVersion.is_active.is_(True),
    )
    active_m = db.scalar(stmt)

    if active_m:
        model_out = ModelVersionOut(
            id=active_m.id,
            workspace_id=active_m.workspace_id,
            algorithm=active_m.algorithm,
            trained_at=active_m.trained_at,
            n_samples=active_m.n_samples,
            metrics=active_m.metrics,
            feature_list=[str(f) for f in active_m.feature_list],
            is_active=active_m.is_active,
        )
        return ActiveModelMetricsOut(
            has_active_model=True,
            active_model=model_out,
            fallback_mode="none",
            message=f"Using trained {active_m.algorithm} model (n={active_m.n_samples})",
        )

    return ActiveModelMetricsOut(
        has_active_model=False,
        active_model=None,
        fallback_mode="rules_only",
        message=(
            "Cold-start mode: scoring leads using explainable 5-part rule engine "
            "until outcome threshold is reached."
        ),
    )


@router.post("/train", response_model=ActiveModelMetricsOut)
def trigger_model_training(
    req: ModelTrainRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ActiveModelMetricsOut:
    """Trigger training pipeline for workspace outcome data."""
    # Checked in Prompt 14 for minimum logged outcomes threshold
    return ActiveModelMetricsOut(
        has_active_model=False,
        active_model=None,
        fallback_mode="rules_only",
        message=(
            f"Training requested for '{req.algorithm}'. "
            f"Minimum {req.min_samples} logged outcomes required."
        ),
    )


@router.get("/dataset/health", response_model=DatasetHealthOut)
def get_dataset_health_endpoint(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> DatasetHealthOut:
    """Get dataset health metrics for ML unlock readiness."""
    health = get_dataset_health(session=db, workspace_id=workspace.id)
    return DatasetHealthOut(**health)


@router.get("/dataset/export")
def export_training_dataset(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Export leak-free training dataset containing snapshotted features."""
    dataset = build_training_dataset(session=db, workspace_id=workspace.id)
    return {"items": dataset, "total": len(dataset)}
