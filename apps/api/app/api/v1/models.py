"""Model version and training endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.ml.pipeline import train_and_evaluate_models
from app.ml.registry import get_active_model, rollback_model_version
from app.ml.shap_explainer import explain_lead_features
from app.models import Lead, LeadFeature, ModelVersion, Place, Workspace
from app.outcomes.dataset import build_training_dataset, get_dataset_health
from app.schemas.models import (
    ActiveLearningLeadOut,
    ActiveModelMetricsOut,
    ModelTrainRequest,
    ModelVersionOut,
    RankingComparisonItem,
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
    feat = (
        db.execute(
            select(LeadFeature)
            .where(
                LeadFeature.lead_id == lead_id,
                LeadFeature.workspace_id == workspace.id,
            )
            .order_by(LeadFeature.computed_at.desc())
        )
        .scalars()
        .first()
    )

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


@router.get("/active-learning", response_model=list[ActiveLearningLeadOut])
def get_active_learning_queue(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> list[ActiveLearningLeadOut]:
    """Retrieve leads with highest learning value for active exploration."""
    stmt = (
        select(Lead, Place)
        .join(Place, Lead.place_id == Place.id)
        .where(
            Lead.workspace_id == workspace.id,
            Lead.status.in_(["new", "shortlisted"]),
        )
    )
    results = db.execute(stmt).all()

    items: list[dict[str, Any]] = []
    for lead, place in results:
        ml_score = lead.ml_score
        rule_score = lead.rule_score or 50.0

        # Check for model uncertainty (probability between 0.35 and 0.65)
        is_uncertain = ml_score is not None and (0.35 <= ml_score <= 0.65)
        # Check for high rule score with thin evidence (few reviews or missing website/phone)
        is_thin_evidence = rule_score >= 60.0 and (
            place.review_count <= 5 or not place.website or not place.email
        )

        if is_uncertain or is_thin_evidence:
            if is_uncertain and ml_score is not None:
                reason = (
                    f"High model uncertainty ({int(ml_score * 100)}% reply probability) "
                    "— outcome provides maximum training information."
                )
                priority = "high"
            else:
                reason = (
                    f"High rule score ({int(rule_score)}) with thin evidence "
                    f"({place.review_count} reviews) — verifies niche market opportunity."
                )
                priority = "medium"

            items.append(
                {
                    "lead_id": lead.id,
                    "place_id": place.id,
                    "name": place.name,
                    "category": place.normalized_category or place.category,
                    "rule_score": lead.rule_score,
                    "ml_score": lead.ml_score,
                    "final_score": lead.final_score,
                    "reason": reason,
                    "learning_priority": priority,
                    "review_count": place.review_count,
                    "rating": place.rating,
                    "has_website": bool(place.website),
                    "has_email": bool(place.email),
                }
            )

    items.sort(
        key=lambda x: (
            0 if x["learning_priority"] == "high" else 1,
            -(x["final_score"] or x["rule_score"] or 0),
        )
    )
    return [ActiveLearningLeadOut(**item) for item in items[:limit]]


@router.get("/ranking-comparison", response_model=list[RankingComparisonItem])
def get_ranking_comparison(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> list[RankingComparisonItem]:
    """Compare top leads ranked by pure rules vs model-blended final score."""
    stmt = (
        select(Lead, Place)
        .join(Place, Lead.place_id == Place.id)
        .where(Lead.workspace_id == workspace.id)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return []

    # Rank by rule score
    sorted_by_rule = sorted(rows, key=lambda r: r[0].rule_score or 0.0, reverse=True)
    rule_ranks = {lead.id: idx + 1 for idx, (lead, _) in enumerate(sorted_by_rule)}

    # Rank by final blended score
    sorted_by_final = sorted(rows, key=lambda r: r[0].final_score or 0.0, reverse=True)
    final_ranks = {lead.id: idx + 1 for idx, (lead, _) in enumerate(sorted_by_final)}

    comparison: list[RankingComparisonItem] = []
    for lead, place in sorted_by_final[:limit]:
        r_rank = rule_ranks.get(lead.id, 999)
        f_rank = final_ranks.get(lead.id, 999)
        shift = r_rank - f_rank
        direction = "up" if shift > 0 else ("down" if shift < 0 else "same")

        comparison.append(
            RankingComparisonItem(
                lead_id=lead.id,
                place_name=place.name,
                category=place.normalized_category or place.category,
                rule_score=round(lead.rule_score or 0.0, 1),
                rule_rank=r_rank,
                ml_score=round(lead.ml_score, 3) if lead.ml_score is not None else None,
                ml_rank=None,
                final_score=round(lead.final_score or 0.0, 1),
                final_rank=f_rank,
                rank_shift=shift,
                shift_direction=direction,
            )
        )

    return comparison
