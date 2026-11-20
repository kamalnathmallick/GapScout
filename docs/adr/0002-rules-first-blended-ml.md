# ADR 0002: Rules-First Scoring Blended with Calibrated Machine Learning

## Status
Accepted

## Context
When a new agency or freelancer opens GapScout, they have zero historical outreach outcome labels. An end-to-end ML model cannot be trained or trusted without labelled outcomes (the cold-start problem). Conversely, purely manual or heuristic scoring fails to learn over time from actual conversion outcomes (e.g. which pitch angles or business profiles actually reply).

## Decision
We implemented a **Two-Stage Blended Scoring Architecture**:
1. **Stage 1 (Cold Start):** Transparent, deterministic rule-based scoring (0-100) combining five explicit dimensions: Pain (25%), Fit (25%), Timing (15%), Reachability (20%), and Evidence (15%). Every score component produces human-readable explanations.
2. **Stage 2 (Cold-Start Gating):** Strict gating requires at least $N \ge 150$ total labelled outcomes and $P \ge 20$ positive outcomes before unlocking machine learning.
3. **Stage 3 (Blended Tournament):** A machine learning tournament trains a baseline regularized Logistic Regression and a challenger HistGradientBoostingClassifier with Platt probability calibration. Once active, the final score blends rules and calibrated ML probabilities:
   $$\text{Final Score} = (1 - w_{\text{ml}}) \times \text{Rule Score} + w_{\text{ml}} \times (\text{ML Probability} \times 100)$$
   where $w_{\text{ml}}$ scales smoothly with dataset size up to 0.70.

## Consequences & Trade-offs
### Advantages:
- **Instant Day-One Utility:** Users receive immediate, explainable rankings without needing prior data.
- **Trust & Explainability:** The "Why this score" drawer shows exact point breakdowns and SHAP feature attributions.
- **Continuous Improvement:** Every logged outcome (replied, meeting, sale, no reply) acts as a high-signal training label.
- **Fail-Safe Fallback:** If concept drift or data corruption occurs, the system automatically falls back to deterministic rule scoring without downtime.
