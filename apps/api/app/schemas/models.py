"""ML Model schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ModelTrainRequest(BaseModel):
    """Trigger training of a new model version."""

    algorithm: str = "lightgbm"
    min_samples: int = 50


class ModelVersionOut(BaseModel):
    """Model version details and evaluation metrics."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    algorithm: str
    trained_at: datetime
    n_samples: int
    metrics: dict[str, Any]
    feature_list: list[str]
    is_active: bool

    model_config = {"from_attributes": True}


class ActiveModelMetricsOut(BaseModel):
    """Metrics for currently active model."""

    has_active_model: bool
    active_model: ModelVersionOut | None = None
    fallback_mode: str = "rules_only"
    message: str
