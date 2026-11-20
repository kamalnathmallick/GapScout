"""Model version and training endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.ml.pipeline import train_and_evaluate_models
from app.ml.registry import get_active_model, rollback_model_version
from app.ml.shap_explainer import explain_lead_features
from app.models import LeadFeature, ModelVersion, Workspace
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
    dataset = build_training_dataset(session=db, workspace_id=workspace.id)
    result = train_and_evaluate_models(
        dataset=dataset,
        workspace_id=workspace.id,
        session=db,
        force=req.algorithm == "force",
    )

    if not result.get("unlocked"):
        return ActiveModelMetricsOut(
            has_active_model=False,
            active_model=None,
            fallback_mode="rules_only",
            message=result.get("message", "Cold-start threshold not met."),
        )

    active_m = get_active_model(db, workspace.id)
    model_out = None
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
        message=result.get("message", "Model trained successfully."),
    )


@router.post("/{version_id}/rollback", response_model=ModelVersionOut)
def rollback_model_endpoint(
    version_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelVersionOut:
    """Roll back active model to a previous verified version."""
    try:
        model = rollback_model_version(
            session=db,
            workspace_id=workspace.id,
            target_version_id=version_id,
        )
        return ModelVersionOut(
            id=model.id,
            workspace_id=model.workspace_id,
            algorithm=model.algorithm,
            trained_at=model.trained_at,
            n_samples=model.n_samples,
            metrics=model.metrics,
            feature_list=[str(f) for f in model.feature_list],
            is_active=model.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/leads/{lead_id}/explanation")
def get_lead_explanation(
    lead_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get top 3 SHAP feature contributions for a lead."""
    feat = db.execute(
        select(LeadFeature)
        .where(
            LeadFeature.lead_id == lead_id,
            LeadFeature.workspace_id == workspace.id,
        )
        .order_by(LeadFeature.computed_at.desc())
    ).scalars().first()

    features_dict = feat.features if feat else {}
    explanations = explain_lead_features(features_dict)
    return {"lead_id": str(lead_id), "explanations": explanations}


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
