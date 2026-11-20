# Changelog

All notable changes to the **GapScout** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-beta] - 2026-11-20

### Added
- **H3 Hexagonal Spatial Engine:** Uber H3 resolution-8 hexagonal indexing with supply-demand opportunity scoring and isotropic smoothing.
- **Interactive Geospatial Web App:** Next.js 16 App Router frontend with deck.gl `H3HexagonLayer` and MapLibre GL vector tiles.
- **Two-Stage Lead Scoring Pipeline:** Deterministic 5-factor cold-start rules (Pain, Fit, Timing, Reachability, Evidence) blended with Platt-calibrated ML tournaments (HistGradientBoosting / Logistic Regression).
- **Model Insights & Active Learning:** Interactive ROC curves, calibration plots, precision@10 metrics, SHAP feature importance charts, model version rollback, and uncertainty-based active learning queues.
- **LLM Enrichment & Grounded Outreach:** Grounded review theme extraction, website audit scoring, channel length caps (WhatsApp $\le 450$ chars, Email $\le 120$ words), mandatory opt-out lines, and zero auto-send human-in-the-loop safeguards.
- **Multi-Tenant Security & Compliance:** Database-level workspace isolation, argon2id password hashing, JWT rotation, DNC list enforcement, 90-day raw data retention pruning, GDPR data export/deletion, and prompt-injection quarantine (`<untrusted_content>`).
- **Comprehensive Quality Suite:** 350+ unit/contract/eval tests, scraper contract regression suites, performance benchmarks (50k places in 7.1s, 5k hexes in 80ms), Playwright end-to-end journey tests, and strict `mypy` / TypeScript CI checks.
- **Agent Skills:** Full suite of Claude Agent Skills (`gapscout-setup`, `gap-scan`, `lead-rank`, `draft-pitch`, `log-outcome`) with `.claude-plugin/manifest.json`.
- **Demo Seeding Pipeline:** `scripts/seed_demo.py` featuring realistic Bangalore Indiranagar & Koramangala commercial cafe intelligence with historical outcome logs.
