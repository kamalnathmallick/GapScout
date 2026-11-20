"""Dynamic rule + ML score blending."""


def compute_blended_score(
    rule_score: float,
    model_probability: float,
    n_samples: int,
    min_samples: int = 150,
    max_samples: int = 1000,
) -> float:
    """Blend rule score (0-100) and ML model probability (0.0-1.0).

    Model weight smoothly scales from 0.30 at cold-start unlock (150 samples)
    up to 0.80 as dataset reaches 1000+ samples.
    """
    rule_score_clamped = max(0.0, min(100.0, float(rule_score)))
    ml_score_0_100 = max(0.0, min(100.0, float(model_probability) * 100.0))

    if n_samples < min_samples:
        return round(rule_score_clamped, 1)

    progress = min(1.0, max(0.0, (n_samples - min_samples) / max(1, (max_samples - min_samples))))
    w_model = 0.30 + (0.50 * progress)  # 0.30 -> 0.80
    w_rule = 1.0 - w_model

    blended = (w_rule * rule_score_clamped) + (w_model * ml_score_0_100)
    return round(blended, 1)
