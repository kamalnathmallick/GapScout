"""ML training pipeline: baseline regularized LR, challenger HGB, calibration, and registry."""

import logging
import uuid
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.ml.gating import check_cold_start_gating
from app.ml.registry import save_and_register_model
from app.models import ModelVersion

logger = logging.getLogger(__name__)

NUMERIC_FEATURES = [
    "rating",
    "review_count",
    "log_review_count",
    "price_level",
    "has_real_website",
    "website_is_https",
    "has_phone",
    "has_named_email",
    "has_generic_email",
    "hours_complete",
    "owner_reply_rate",
    "negative_review_share",
    "days_since_last_review",
    "hex_opportunity_score",
    "hex_supply_count",
    "hex_demand_proxy",
    "distance_to_nearest_competitor_m",
    "website_audit_score",
    "number_of_review_pain_themes",
]


def extract_feature_matrix(
    dataset: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Convert dataset dictionaries into feature matrix X and label vector y."""
    feature_names = list(NUMERIC_FEATURES)
    rows_x: list[list[float]] = []
    rows_y: list[int] = []
    timestamps: list[str] = []

    for item in dataset:
        feat_dict = item.get("features", {})
        row = []
        for name in NUMERIC_FEATURES:
            val = feat_dict.get(name)
            if val is None or val == "":
                row.append(np.nan)
            else:
                try:
                    row.append(float(val))
                except (ValueError, TypeError):
                    row.append(np.nan)
        rows_x.append(row)
        rows_y.append(int(item.get("label", 0)))
        timestamps.append(item.get("contacted_at", ""))

    X = np.array(rows_x, dtype=float)
    y = np.array(rows_y, dtype=int)
    return X, y, feature_names, timestamps


def compute_precision_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int = 10) -> float:
    """Calculate precision in the top k predicted highest probability instances."""
    if len(y_true) == 0:
        return 0.0
    k_clamped = min(k, len(y_true))
    top_indices = np.argsort(y_prob)[::-1][:k_clamped]
    return float(np.mean(y_true[top_indices]))


def train_and_evaluate_models(
    dataset: list[dict[str, Any]],
    workspace_id: uuid.UUID,
    session: Session | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Train baseline LogisticRegression and challenger HistGradientBoostingClassifier."""
    unlocked, message = check_cold_start_gating(dataset, force=force)
    if not unlocked:
        return {
            "unlocked": False,
            "has_active_model": False,
            "message": message,
            "metrics": {},
        }

    X, y, feature_names, timestamps = extract_feature_matrix(dataset)

    # Impute missing numeric values explicitly
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    # Time-based split if >= 100 samples and ordered timestamps exist; otherwise stratified split
    n_samples = len(y)
    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        return {
            "unlocked": False,
            "has_active_model": False,
            "message": "Dataset lacks positive or negative variety for classification.",
            "metrics": {},
        }

    if n_samples >= 100 and timestamps and timestamps[0] <= timestamps[-1]:
        split_idx = int(0.75 * n_samples)
        X_train, X_val = X_imputed[:split_idx], X_imputed[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
    else:
        X_train, X_val, y_train, y_val = train_test_split(
            X_imputed, y, test_size=0.25, random_state=42, stratify=y
        )

    # 1. Baseline Model: Standardized Regularized Logistic Regression with Platt scaling
    baseline_lr = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, max_iter=1000, random_state=42)),
        ]
    )
    cv_folds = min(3, np.min(np.bincount(y_train)))
    if cv_folds >= 2:
        calibrated_baseline = CalibratedClassifierCV(
            estimator=baseline_lr, method="sigmoid", cv=cv_folds
        )
        calibrated_baseline.fit(X_train, y_train)
        baseline_model = calibrated_baseline
    else:
        baseline_lr.fit(X_train, y_train)
        baseline_model = baseline_lr

    base_probs = baseline_model.predict_proba(X_val)[:, 1]
    base_auc = roc_auc_score(y_val, base_probs) if len(np.unique(y_val)) > 1 else 0.5
    base_prauc = average_precision_score(y_val, base_probs) if len(np.unique(y_val)) > 1 else 0.0

    # 2. Challenger Model: HistGradientBoostingClassifier
    challenger_hgb = HistGradientBoostingClassifier(
        max_iter=100, min_samples_leaf=3, random_state=42
    )
    if cv_folds >= 2:
        calibrated_challenger = CalibratedClassifierCV(
            estimator=challenger_hgb, method="sigmoid", cv=cv_folds
        )
        calibrated_challenger.fit(X_train, y_train)
        challenger_model = calibrated_challenger
    else:
        challenger_hgb.fit(X_train, y_train)
        challenger_model = challenger_hgb

    challenger_probs = challenger_model.predict_proba(X_val)[:, 1]
    challenger_auc = roc_auc_score(y_val, challenger_probs) if len(np.unique(y_val)) > 1 else 0.5
    challenger_prauc = (
        average_precision_score(y_val, challenger_probs) if len(np.unique(y_val)) > 1 else 0.0
    )

    # 3. Model Tournament: Select winner
    if challenger_auc >= base_auc:
        winner_name = "HistGradientBoostingClassifier"
        winner_model = challenger_model
        winner_auc = challenger_auc
        winner_prauc = challenger_prauc
        winner_probs = challenger_probs
    else:
        winner_name = "LogisticRegression"
        winner_model = baseline_model
        winner_auc = base_auc
        winner_prauc = base_prauc
        winner_probs = base_probs

    p10 = compute_precision_at_k(y_val, winner_probs, k=10)
    brier = float(brier_score_loss(y_val, winner_probs))
    pos_rate = float(np.mean(y_val))
    lift = round(p10 / pos_rate, 2) if pos_rate > 0 else 1.0

    metrics = {
        "roc_auc": round(float(winner_auc), 4),
        "pr_auc": round(float(winner_prauc), 4),
        "precision_at_10": round(float(p10), 4),
        "brier_score": round(brier, 4),
        "lift_over_rules": lift,
        "n_samples": n_samples,
        "baseline_auc": round(float(base_auc), 4),
        "challenger_auc": round(float(challenger_auc), 4),
    }

    model_record: ModelVersion | None = None
    if session:
        # Wrap model with preprocessor imputer
        full_pipeline = Pipeline([("imputer", imputer), ("estimator", winner_model)])
        model_record = save_and_register_model(
            session=session,
            workspace_id=workspace_id,
            algorithm=winner_name,
            trained_pipeline=full_pipeline,
            metrics=metrics,
            feature_list=feature_names,
            n_samples=n_samples,
        )

    return {
        "unlocked": True,
        "has_active_model": model_record.is_active if model_record else True,
        "active_model_id": str(model_record.id) if model_record else None,
        "algorithm": winner_name,
        "metrics": metrics,
        "feature_list": feature_names,
        "message": f"Successfully trained and evaluated {winner_name} (ROC-AUC={winner_auc:.3f}).",
    }
