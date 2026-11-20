"""Tests for Prompt 14: ML training pipeline, gating, signal recovery, blending, and rollback."""

import random
import uuid

import numpy as np
import pytest

from app.ml.blending import compute_blended_score
from app.ml.drift import check_feature_drift
from app.ml.gating import check_cold_start_gating
from app.ml.pipeline import train_and_evaluate_models
from app.ml.registry import (
    get_active_model,
    rollback_model_version,
    save_and_register_model,
)
from app.ml.shap_explainer import explain_lead_features
from app.models import Workspace


@pytest.fixture
def workspace(db_session):
    ws = Workspace(name="ML Test Workspace")
    db_session.add(ws)
    db_session.commit()
    return ws


def generate_synthetic_outcomes(n_samples: int = 200, seed: int = 42) -> list[dict]:
    """Generate synthetic leads with a planted signal:

    Leads with low rating (< 3.8) and named email have an 85% reply rate,
    while other leads have a 15% reply rate.
    """
    rng = random.Random(seed)
    dataset = []

    for i in range(n_samples):
        rating = round(rng.uniform(2.5, 4.9), 1)
        has_named_email = 1 if rng.random() > 0.4 else 0
        hex_opp = round(rng.uniform(20.0, 95.0), 1)
        review_count = rng.randint(5, 300)

        # Planted signal: high pain + reachability = high conversion
        prob = 0.85 if rating < 3.8 and has_named_email == 1 and hex_opp > 50 else 0.15

        label = 1 if rng.random() < prob else 0

        dataset.append(
            {
                "lead_id": str(uuid.uuid4()),
                "contacted_at": f"2026-11-{(i % 28) + 1:02d}T10:00:00",
                "label": label,
                "secondary_label": "replied" if label == 1 else "no_reply",
                "features": {
                    "rating": rating,
                    "review_count": review_count,
                    "log_review_count": round(np.log1p(review_count), 2),
                    "price_level": 2,
                    "has_real_website": 1 if rng.random() > 0.3 else 0,
                    "website_is_https": 1,
                    "has_phone": 1,
                    "has_named_email": has_named_email,
                    "has_generic_email": 1 if rng.random() > 0.5 else 0,
                    "hours_complete": 1,
                    "owner_reply_rate": round(rng.uniform(0.0, 1.0), 2),
                    "negative_review_share": round(rng.uniform(0.0, 0.4), 2),
                    "days_since_last_review": rng.randint(2, 60),
                    "hex_opportunity_score": hex_opp,
                    "hex_supply_count": rng.randint(2, 25),
                    "hex_demand_proxy": round(rng.uniform(10.0, 80.0), 1),
                    "distance_to_nearest_competitor_m": rng.randint(50, 1500),
                    "website_audit_score": round(rng.uniform(30.0, 90.0), 1),
                    "number_of_review_pain_themes": rng.randint(0, 5),
                },
            }
        )
    return dataset


def test_cold_start_gating():
    """Verify gating stays in rules-only mode when data is thin."""
    # Empty dataset
    unlocked, msg = check_cold_start_gating([])
    assert not unlocked
    assert "Cold-start active" in msg

    # Insufficient samples (< 150)
    thin_data = [{"label": 1 if i < 10 else 0} for i in range(50)]
    unlocked, msg = check_cold_start_gating(thin_data)
    assert not unlocked
    assert "Need 100 more outcomes" in msg

    # 150 samples but insufficient positives (< 20)
    low_positives = [{"label": 1 if i < 5 else 0} for i in range(160)]
    unlocked, msg = check_cold_start_gating(low_positives)
    assert not unlocked
    assert "positive replies" in msg


def test_signal_recovery_on_synthetic_data(db_session, workspace):
    """Verify model recovers planted signal with AUC clearly above 0.5 (target > 0.70)."""
    dataset = generate_synthetic_outcomes(n_samples=250, seed=123)

    result = train_and_evaluate_models(
        dataset=dataset,
        workspace_id=workspace.id,
        session=db_session,
    )

    assert result["unlocked"] is True
    assert result["has_active_model"] is True

    metrics = result["metrics"]
    roc_auc = metrics["roc_auc"]
    assert roc_auc >= 0.70, f"Expected ROC-AUC >= 0.70 recovering planted signal, got {roc_auc:.3f}"
    assert metrics["brier_score"] < 0.25
    assert metrics["precision_at_10"] >= 0.50

    # Model was registered in model_versions
    active_m = get_active_model(db_session, workspace.id)
    assert active_m is not None
    assert active_m.is_active is True
    assert active_m.metrics["roc_auc"] == roc_auc


def test_rule_ml_score_blending():
    """Verify blend smoothly weights model from 0.3 to 0.8 as sample size grows."""
    rule_score = 80.0
    model_prob = 0.50  # 50 points

    # Below cold-start threshold: pure rules
    score_100 = compute_blended_score(rule_score, model_prob, n_samples=100)
    assert score_100 == 80.0

    # Exactly at unlock (150 samples): weight is 30% model, 70% rules
    # 0.70 * 80 + 0.30 * 50 = 56 + 15 = 71.0
    score_150 = compute_blended_score(rule_score, model_prob, n_samples=150)
    assert abs(score_150 - 71.0) < 0.5

    # At 1000+ samples: weight is 80% model, 20% rules
    # 0.20 * 80 + 0.80 * 50 = 16 + 40 = 56.0
    score_1000 = compute_blended_score(rule_score, model_prob, n_samples=1000)
    assert abs(score_1000 - 56.0) < 0.5


def test_model_activation_tournament_and_rollback(db_session, workspace):
    """Verify tournament activation rules and one-click rollback."""
    # 1. Register Model A (AUC = 0.72)
    model_a = save_and_register_model(
        session=db_session,
        workspace_id=workspace.id,
        algorithm="LogisticRegression",
        trained_pipeline={"model": "A"},
        metrics={"roc_auc": 0.72},
        feature_list=["rating"],
        n_samples=160,
    )
    assert model_a.is_active is True

    # 2. Register Model B with lower AUC (0.68) -> Should NOT activate
    model_b = save_and_register_model(
        session=db_session,
        workspace_id=workspace.id,
        algorithm="HistGradientBoostingClassifier",
        trained_pipeline={"model": "B"},
        metrics={"roc_auc": 0.68},
        feature_list=["rating"],
        n_samples=180,
    )
    assert model_b.is_active is False
    assert get_active_model(db_session, workspace.id).id == model_a.id

    # 3. Register Model C with higher AUC (0.81) -> Should activate and deactivate Model A
    model_c = save_and_register_model(
        session=db_session,
        workspace_id=workspace.id,
        algorithm="HistGradientBoostingClassifier",
        trained_pipeline={"model": "C"},
        metrics={"roc_auc": 0.81},
        feature_list=["rating"],
        n_samples=220,
    )
    assert model_c.is_active is True
    assert get_active_model(db_session, workspace.id).id == model_c.id

    # 4. Rollback to Model A
    restored = rollback_model_version(
        session=db_session,
        workspace_id=workspace.id,
        target_version_id=model_a.id,
    )
    assert restored.id == model_a.id
    assert restored.is_active is True
    assert get_active_model(db_session, workspace.id).id == model_a.id


def test_shap_explanation_extraction():
    """Verify top 3 feature impact explanations with human-readable reasons."""
    features = {
        "rating": 3.2,
        "has_named_email": 1,
        "hex_opportunity_score": 85.0,
        "website_audit_score": 40.0,
    }

    explanations = explain_lead_features(features, top_k=3)
    assert len(explanations) == 3
    for exp in explanations:
        assert "feature" in exp
        assert "impact" in exp
        assert "reason" in exp
        assert len(exp["reason"]) > 10


def test_drift_detection_warning():
    """Verify drift detection flags large shifts between inference and training features."""
    train_data = [{"features": {"rating": 4.5, "review_count": 100}} for _ in range(50)]
    # Shifted inference data (rating dropped to 2.0)
    drifted_inf = [{"rating": 2.0, "review_count": 100} for _ in range(50)]

    drift_report = check_feature_drift(train_data, drifted_inf)
    assert drift_report["has_drift"] is True
    assert len(drift_report["warnings"]) >= 1
    assert "rating" in drift_report["warnings"][0]
