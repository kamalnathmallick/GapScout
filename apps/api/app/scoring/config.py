"""Configuration loader for the Rule-Based Lead Scoring engine."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    pain: float = 25.0
    fit: float = 25.0
    timing: float = 15.0
    reachability: float = 20.0
    evidence: float = 15.0


class PainConfig(BaseModel):
    no_website_points: float = 10.0
    not_https_points: float = 4.0
    low_rating_threshold: float = 4.0
    low_rating_points: float = 6.0
    unanswered_negative_reviews_points: float = 5.0


class FitConfig(BaseModel):
    category_match_points: float = 15.0
    rating_range_points: float = 5.0
    region_match_points: float = 5.0
    default_category_points: float = 10.0
    default_rating_points: float = 5.0


class TimingConfig(BaseModel):
    recent_review_days_threshold: int = 90
    recent_negative_review_points: float = 7.0
    new_business_days_threshold: int = 180
    new_business_points: float = 5.0
    high_opportunity_hex_threshold: float = 70.0
    high_opportunity_hex_points: float = 3.0


class ReachabilityConfig(BaseModel):
    named_email_points: float = 12.0
    generic_email_points: float = 7.0
    phone_points: float = 6.0
    social_or_website_points: float = 2.0


class EvidenceConfig(BaseModel):
    high_review_count_threshold: int = 20
    high_review_count_points: float = 5.0
    hours_complete_points: float = 3.0
    verified_location_points: float = 4.0
    has_engagement_points: float = 3.0


class ScoringConfig(BaseModel):
    """Complete rule scoring configuration."""

    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    pain: PainConfig = Field(default_factory=PainConfig)
    fit: FitConfig = Field(default_factory=FitConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    reachability: ReachabilityConfig = Field(default_factory=ReachabilityConfig)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)


def load_scoring_config(config_path: str | Path | None = None) -> ScoringConfig:
    """Load scoring configuration from YAML file or return defaults."""
    candidate_paths: list[Path] = []
    if config_path:
        candidate_paths.append(Path(config_path))
    else:
        # Default locations to search
        candidate_paths.extend(
            [
                Path("/app/config/scoring.yaml"),
                Path(__file__).resolve().parent.parent.parent / "config" / "scoring.yaml",
                Path(__file__).resolve().parent.parent.parent.parent / "config" / "scoring.yaml",
            ]
        )

    for p in candidate_paths:
        if p.is_file():
            try:
                with open(p, encoding="utf-8") as f:
                    data: dict[str, Any] = yaml.safe_load(f) or {}
                return ScoringConfig(**data)
            except Exception:
                pass

    return ScoringConfig()
