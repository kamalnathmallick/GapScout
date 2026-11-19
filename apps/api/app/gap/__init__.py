"""Market gap and opportunity engine package."""

from app.gap.anchors import classify_anchor_category
from app.gap.config import GapConfig, load_gap_config
from app.gap.engine import compute_gap_metrics

__all__ = [
    "GapConfig",
    "classify_anchor_category",
    "compute_gap_metrics",
    "load_gap_config",
]
