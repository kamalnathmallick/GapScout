"""Configuration loader for the Gap Analysis engine."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

DEFAULT_ANCHOR_WEIGHTS = {
    "cafe": {
        "office": 2.5,
        "college": 2.0,
        "transit": 1.5,
        "mall": 1.2,
        "apartment": 1.0,
        "hospital": 0.5,
    },
    "restaurant": {
        "office": 1.8,
        "mall": 2.0,
        "apartment": 1.5,
        "transit": 1.2,
        "college": 1.0,
    },
    "gym": {
        "apartment": 2.5,
        "office": 1.8,
        "mall": 1.0,
        "transit": 1.0,
    },
    "salon": {
        "apartment": 2.2,
        "mall": 1.8,
        "office": 1.2,
    },
    "dental clinic": {
        "apartment": 2.5,
        "hospital": 1.5,
        "office": 1.0,
    },
    "coaching centre": {
        "college": 2.5,
        "transit": 2.0,
        "apartment": 1.8,
        "office": 0.8,
    },
    "default": {
        "office": 1.5,
        "apartment": 1.5,
        "mall": 1.0,
        "transit": 1.0,
        "college": 1.0,
        "hospital": 0.8,
    },
}


class GapConfig(BaseModel):
    """Gap analysis hyperparameters and weights."""

    smoothing_constant: float = 1.0
    quality_gap_weight: float = 15.0
    k_ring_weight: float = 0.35
    anchor_weights: dict[str, dict[str, float]] = Field(
        default_factory=lambda: DEFAULT_ANCHOR_WEIGHTS
    )
    quantiles: dict[str, float] = Field(
        default_factory=lambda: {
            "underserved_percentile": 0.67,
            "oversaturated_percentile": 0.33,
        }
    )


def load_gap_config(config_path: str | Path | None = None) -> GapConfig:
    """Load gap analysis config from YAML file with fallback to defaults."""
    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.extend(
        [
            Path("config/gap.yaml"),
            Path("apps/api/config/gap.yaml"),
            Path("/app/config/gap.yaml"),
            Path(__file__).resolve().parents[2] / "config" / "gap.yaml",
            Path(__file__).resolve().parents[3] / "config" / "gap.yaml",
        ]
    )

    for p in search_paths:
        if p.exists() and p.is_file():
            try:
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return GapConfig(**data)
            except Exception:
                pass

    return GapConfig()
