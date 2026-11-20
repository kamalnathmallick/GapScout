"""Settings and Workspace Caps schemas."""

from pydantic import BaseModel, Field


class WorkspaceCapsOut(BaseModel):
    """Workspace execution caps and data retention settings."""

    max_cells_per_job: int
    max_places_per_job: int
    daily_llm_cost_cap_usd: float
    data_retention_days: int

    model_config = {"from_attributes": True}


class WorkspaceCapsUpdate(BaseModel):
    """Update workspace limits and retention policy."""

    max_cells_per_job: int | None = Field(default=None, ge=1, le=5000)
    max_places_per_job: int | None = Field(default=None, ge=10, le=50000)
    daily_llm_cost_cap_usd: float | None = Field(default=None, ge=0.5, le=100.0)
    data_retention_days: int | None = Field(default=None, ge=7, le=365)


class ScoringWeightsOut(BaseModel):
    """Scoring component weights and configuration."""

    weights: dict[str, float]
    is_custom: bool


class ScoringWeightsUpdate(BaseModel):
    """Update custom scoring weights."""

    weights: dict[str, float]


class ApiUsageOut(BaseModel):
    """API and LLM usage statistics."""

    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    cost_today_usd: float
    daily_cost_cap_usd: float
    remaining_budget_today_usd: float
