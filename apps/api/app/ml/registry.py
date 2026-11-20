"""Model registry: versioning, safe rollout, artifact serialization, and rollback."""

import logging
import pickle
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ModelVersion

logger = logging.getLogger(__name__)

ARTIFACT_BASE_DIR = Path("/tmp/gapscout_models")


def get_active_model(session: Session, workspace_id: uuid.UUID) -> ModelVersion | None:
    """Fetch currently active model version for workspace."""
    stmt = select(ModelVersion).where(
        ModelVersion.workspace_id == workspace_id,
        ModelVersion.is_active.is_(True),
    )
    return session.execute(stmt).scalar_one_or_none()


def save_and_register_model(
    session: Session,
    workspace_id: uuid.UUID,
    algorithm: str,
    trained_pipeline: Any,
    metrics: dict[str, Any],
    feature_list: list[str],
    n_samples: int,
) -> ModelVersion:
    """Save model artifact, register in model_versions, and activate if better than current."""
    ARTIFACT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    version_id = uuid.uuid4()
    artifact_path = ARTIFACT_BASE_DIR / f"{workspace_id}_{version_id}.pkl"

    with open(artifact_path, "wb") as f:
        pickle.dump(trained_pipeline, f)

    current_active = get_active_model(session, workspace_id)
    new_auc = metrics.get("roc_auc", 0.5)

    should_activate = True
    if current_active and isinstance(current_active.metrics, dict):
        current_auc = current_active.metrics.get("roc_auc", 0.5)
        if new_auc < current_auc:
            should_activate = False
            logger.info(
                "New model (%s AUC=%.3f) did not beat current active (%s AUC=%.3f). "
                "Kept as candidate.",
                algorithm,
                new_auc,
                current_active.algorithm,
                current_auc,
            )

    if should_activate:
        # Deactivate previous active models
        session.execute(
            update(ModelVersion)
            .where(ModelVersion.workspace_id == workspace_id)
            .values(is_active=False)
        )

    model_ver = ModelVersion(
        id=version_id,
        workspace_id=workspace_id,
        algorithm=algorithm,
        n_samples=n_samples,
        metrics=metrics,
        feature_list=feature_list,
        artifact_path=str(artifact_path),
        is_active=should_activate,
    )
    session.add(model_ver)
    session.commit()
    session.refresh(model_ver)
    return model_ver


def rollback_model_version(
    session: Session,
    workspace_id: uuid.UUID,
    target_version_id: uuid.UUID,
) -> ModelVersion:
    """Roll back active model to a previous verified model version."""
    target = session.get(ModelVersion, target_version_id)
    if not target or target.workspace_id != workspace_id:
        raise ValueError(
            f"Model version {target_version_id} not found for workspace {workspace_id}"
        )

    session.execute(
        update(ModelVersion)
        .where(ModelVersion.workspace_id == workspace_id)
        .values(is_active=False)
    )
    target.is_active = True
    session.commit()
    session.refresh(target)
    logger.info(
        "Rolled back workspace %s active model to %s (%s)",
        workspace_id,
        target.id,
        target.algorithm,
    )
    return target
