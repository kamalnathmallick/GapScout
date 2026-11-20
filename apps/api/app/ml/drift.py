"""Feature distribution drift detection between inference leads and training dataset."""

import math
from typing import Any


def check_feature_drift(
    training_dataset: list[dict[str, Any]],
    inference_features: list[dict[str, Any]],
    threshold_z: float = 2.0,
) -> dict[str, Any]:
    """Compare inference feature distributions to training baseline.

    Returns warnings if feature distribution has drifted significantly.
    """
    if not training_dataset or not inference_features:
        return {"has_drift": False, "warnings": []}

    numeric_keys = [
        "rating",
        "review_count",
        "hex_opportunity_score",
        "website_audit_score",
        "distance_to_nearest_competitor_m",
    ]

    warnings: list[str] = []

    for key in numeric_keys:
        train_vals = [
            float(r["features"][key])
            for r in training_dataset
            if key in r.get("features", {}) and r["features"][key] is not None
        ]
        inf_vals = [float(f[key]) for f in inference_features if key in f and f[key] is not None]

        if len(train_vals) < 10 or len(inf_vals) < 10:
            continue

        train_mean = sum(train_vals) / len(train_vals)
        train_var = sum((x - train_mean) ** 2 for x in train_vals) / len(train_vals)
        train_std = math.sqrt(train_var) if train_var > 1e-6 else 1.0

        inf_mean = sum(inf_vals) / len(inf_vals)
        z_shift = abs(inf_mean - train_mean) / train_std

        if z_shift >= threshold_z:
            warnings.append(
                f"Feature '{key}' drifted by {z_shift:.2f} standard deviations "
                f"(train_mean={train_mean:.2f}, current_mean={inf_mean:.2f})"
            )

    return {
        "has_drift": len(warnings) > 0,
        "warnings": warnings,
    }
