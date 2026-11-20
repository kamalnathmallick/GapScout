"""Cold-start gating for ML model training and scoring."""

from typing import Any

from app.config import get_settings


def check_cold_start_gating(
    dataset: list[dict[str, Any]],
    force: bool = False,
) -> tuple[bool, str]:
    """Determine if enough labelled outcome data exists to train the ML challenger."""
    if force:
        return True, "Forced training mode enabled for verification."

    settings = get_settings()
    min_labels = getattr(settings, "ml_min_labels", 150)
    min_positives = getattr(settings, "ml_min_positives", 20)

    total_samples = len(dataset)
    positives = sum(1 for row in dataset if row.get("label") == 1)

    if total_samples < min_labels:
        return (
            False,
            f"Cold-start active: {total_samples}/{min_labels} labelled outcomes. "
            f"Need {min_labels - total_samples} more outcomes to unlock ML training.",
        )

    if positives < min_positives:
        return (
            False,
            f"Cold-start active: {positives}/{min_positives} positive replies. "
            f"Need {min_positives - positives} more positive replies to unlock ML training.",
        )

    return True, f"Unlocked: {total_samples} samples with {positives} positive outcomes."
