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


class ActiveLearningLeadOut(BaseModel):
    """Lead suggested for active learning contact."""

    lead_id: uuid.UUID
    place_id: uuid.UUID
    name: str
    category: str | None = None
    rule_score: float | None = None
    ml_score: float | None = None
    final_score: float | None = None
    reason: str
    learning_priority: str  # "high" | "medium"
    review_count: int = 0
    rating: float | None = None
    has_website: bool = False
    has_email: bool = False


class RankingComparisonItem(BaseModel):
    """Comparison item between rule-only ranking and ML blended ranking."""

    lead_id: uuid.UUID
    place_name: str
    category: str | None = None
    rule_score: float
    rule_rank: int
    ml_score: float | None = None
    ml_rank: int | None = None
    final_score: float
    final_rank: int
    rank_shift: int
    shift_direction: str  # "up" | "down" | "same"
