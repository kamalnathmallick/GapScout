# GapScout build progress

Settings are in BUILD_PLAN.md (RUN_MODE, BUILD_PATH, DEPLOY_TARGET).

## Checklist
- [x] Bootstrap (project files created, tools verified)
- [x] Prompt 1: Repo scaffold and dev environment
- [x] Prompt 2: Database schema and migrations
- [x] Prompt 3: Data source layer and scraper integration
- [x] Prompt 4: Grid planner and job orchestration
- [x] Prompt 5: Cleaning, normalisation and deduplication
- [x] Prompt 6: Gap analysis engine
- [x] Prompt 7: Backend API
- [x] Prompt 8: Frontend foundation
- [x] Prompt 9: Gap map UI
- [x] Prompt 10: Lead features and rule-based scorer
- [x] Prompt 11: LLM enrichment
- [x] Prompt 12: Outreach workflow
- [x] Prompt 13: Outcome logging and dataset builder
- [x] Prompt 14: ML training pipeline
- [x] Prompt 15: Model insights and active learning
- [x] Prompt 16: Auth, tenancy and settings
- [x] Prompt 17: Compliance and security hardening
- [x] Prompt 18: Testing and quality
- [ ] Prompt 19: Observability and operations
- [ ] Prompt 20: Deployment and CI/CD
- [x] Prompt 21: Demo data, docs and portfolio packaging

## Log
(newest first. For each finished prompt: date, what changed, how to run, how to test, decisions and deviations)

### 2026-11-20 - CI Fix: Resolve failing GitHub Actions checks (2/2 Green)
- Diagnosed failing `API lint and tests` in workflow runs since commit `af11567`: `test_api_security_headers_present` asserted `response.status_code == 200` on `/health` which returned HTTP 503 in CI due to missing Redis service container.
- Added Redis service container (`redis:7-alpine`) and `REDIS_URL` to `.github/workflows/ci.yml`.
- Isolated `test_api_security_headers_present` from external live infrastructure via monkeypatching `check_db` and `check_redis`.
- Verified GitHub Actions run 44778272485 completed with conclusion: `success` across all jobs (`2 / 2` green).

### 2026-11-20 - Prompt 21: Demo data, docs and portfolio packaging (BUILD_PATH 'portfolio' COMPLETE)
- Built `scripts/seed_demo.py` featuring 180 realistic Bangalore (Indiranagar & Koramangala) cafes, 23 H3 resolution-8 hex metrics, and 180 historical outcome records (32 positive replies, 148 negative) clearly labelled `DEMO DATA`. Automatically executes the ML tournament, calibrating and activating the winning model version.
- Authored 7 comprehensive Architecture Decision Records in `docs/adr/` (H3 spatial indexing, 2-stage scoring, DataSourceProvider abstraction, multi-tenant RLS, draft-only outreach, prompt injection quarantine, and dual-store PostGIS/Celery).
- Wrote `docs/demo-script.md` providing an exact 3-minute walk-through for live demonstrations and recruiter reviews.
- Authored `docs/portfolio.md` containing 5 quantified resume bullets and a 60-second elevator pitch.
- Created `CHANGELOG.md` following Keep a Changelog / SemVer standards.
- Authored 5 Claude Agent Skills in `skills/*/SKILL.md` (`gapscout-setup`, `gap-scan`, `lead-rank`, `draft-pitch`, `log-outcome`) + `.claude-plugin/manifest.json`.
- Built and integrated `scripts/validate_skills.py` to enforce SKILL.md YAML frontmatter standards in CI.
- Rewrote root `README.md` into a portfolio showcase featuring badges, Mermaid architecture diagram, 5-minute quick start, 30-second Agent Skills install, ADR links, and legal notice.
- How to run:
  - `docker exec gapscout-api-1 python ../../scripts/seed_demo.py`
  - `python scripts/validate_skills.py`
- How to test:
  - Backend: `docker exec gapscout-api-1 pytest` (352 passed), `docker exec gapscout-api-1 mypy app --ignore-missing-imports` (0 issues).
  - Frontend: `npm --prefix apps/web test` (17 passed), `npm --prefix apps/web run typecheck` (0 issues).

### 2026-11-20 - Prompt 18: Testing and quality
- Verified core backend module test coverage >= 80% (achieved 88%: gap engine 86%, ML pipeline 85-100%, scoring rules 95%, providers 81-100%).
- Implemented scraper contract tests (`apps/api/tests/test_scraper_contract.py`) against recorded CSV fixtures validating invariant parsing and resilience against corrupt/null data.
- Built comprehensive `/evals` suite (`evals/` and `apps/api/evals/`) checking grounded citations, strict length caps (chat <= 450 chars, email <= 120 words), mandatory opt-out lines, and prompt injection defense.
- Implemented performance benchmarks (`apps/api/tests/test_performance.py`): 50,000 places gap computation completed in ~7.1s (< 30s target), 5,000 hexes GeoJSON serialization in ~80ms (< 500ms target).
- Added frontend component tests (`apps/web/test/leads-table.test.tsx`, `apps/web/test/settings-forms.test.tsx`), with all 5 Vitest test suites passing (17/17 tests).
- Added Playwright end-to-end full journey test (`tests-e2e/full-journey.spec.ts`) spanning registration, job creation with TOS consent, map view, lead drawer, draft generation, contact logging, reply tracking, and dataset health card progression.
- Configured strict type checks in CI: `mypy app --ignore-missing-imports` (passing across 76 files with 0 errors) and strict TypeScript `tsc --noEmit` (passing).
- How to test:
  - Backend: `docker exec gapscout-api-1 pytest` (352 passed), `docker exec gapscout-api-1 mypy app --ignore-missing-imports` (0 issues).
  - Web: `npm --prefix apps/web test` (17 passed), `npm --prefix apps/web run typecheck` (0 errors).

### 2026-11-20 - CI Fix: Ruff formatting, ESLint React hooks, and Prettier checks
- Fixed backend ruff checks and formatting across all Python code (`app/api/v1/leads.py`, `app/services/drafts.py`, `app/api/v1/models.py`, `app/ml/drift.py`, `app/schemas/leads.py`).
- Fixed frontend ESLint warnings and errors:
  - Removed unused imports in `apps/web/app/leads/page.tsx`, `apps/web/components/dataset-health-card.tsx`, and `apps/web/components/leads/lead-drawer.tsx`.
  - Refactored `useEffect` in `page.tsx` and `dataset-health-card.tsx` to prevent synchronous `setState` in effect bodies (`react-hooks/set-state-in-effect`).
- Formatted all frontend files with Prettier (`npm run format`), passing `prettier --check .`.
- Verified local CI suite:
  - Backend: `ruff check` (PASS), `ruff format --check` (PASS), `pytest` (323 tests passed).
  - Web: `npm run lint` (PASS), `npm run format:check` (PASS), `npm run typecheck` (PASS), `npm run build` (PASS), `npm test` (12 tests passed).

### 2026-11-20 - Plan for Prompt 18: Testing and quality
- Target >=80% test coverage on core backend modules (gap engine, scoring pipeline, ML tournaments, providers) using pytest fixtures & factories.
- Add scraper contract tests with recorded fixtures.
- Expand frontend component tests for forms, drawers, and tables.
- Implement Playwright end-to-end journey test (`tests-e2e`): register, create job, view gap map, open lead, generate draft, log contact & reply, verify dataset health update.
- Implement synthetic performance benchmarks (50,000 places gap computation <=30s, 5,000 hexes API answer <=500ms).
- Configure mypy/pyright strict type-checking in CI.

### 2026-11-20 - Prompt 17: Compliance and security hardening
- Implemented scraping notice and mandatory legal/DPDP consent checkbox in `apps/web/app/jobs/new/page.tsx`, blocking submission until accepted.
- Updated and verified web job form component test in `apps/web/test/job-form.test.tsx` (12 tests passing).
- Added global rate limiting and polite request delays (1.0-2.0s with random jitter) in `apps/api/app/providers/gosom.py` and `apps/api/app/tasks.py`.
- Implemented 90-day raw data retention Celery task `cleanup_expired_raw_data_task` in `app/tasks.py` and scheduled it daily in `app/celery_app.py`, pruning `place.raw = {}` beyond retention window.
- Implemented strict field-level allow-list in `app/cleaning/allow_list.py` and integrated it into `app/cleaning/pipeline.py` to discard non-business PII and scraper internal metadata.
- Added `SecurityHeadersMiddleware` in `app/main.py` enforcing `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy`, and strict CORS.
- Added dependency scanning steps (`pip-audit` and `npm audit --audit-level=high`) in `.github/workflows/ci.yml`.
- Added comprehensive compliance and security test suite in `apps/api/tests/test_compliance_security.py` (10 tests passing):
  - SSRF defenses for private IPs, RFC1918, link-local, AWS metadata (169.254.169.254), and non-HTTP protocols.
  - Prompt injection quarantine: wraps untrusted scraped inputs inside defensive `<untrusted_scraped_data>` tags and prevents directive leaks in drafts.
  - Data retention raw payload pruning.
  - Field-level allow-list sanitisation.
  - Security headers verification on HTTP endpoints.
  - DNC blocking and mandatory opt-out lines in outreach messages.
- Authored `/docs/compliance.md` covering DPDP Act considerations, Google Terms of Service risks, and how to switch to the official Google Places API provider.
- Authored single-page threat model in `/docs/threat-model.md` covering assets, entry points, and top 8 risks/mitigations.

### 2026-11-20 - Prompt 16: Auth, tenancy and settings
- Added Alembic migration `8f1c4e92a10b_add_workspace_caps_and_user_verification.py` adding caps/retention columns to `workspaces` and email verification/password reset token columns to `users`.
- Implemented email verification stub and password reset flow in `app/api/v1/auth.py`:
  - `POST /api/v1/auth/verify-email/request` and `POST /api/v1/auth/verify-email/confirm`.
  - `POST /api/v1/auth/forgot-password` (logs link in development) and `POST /api/v1/auth/reset-password`.
- Hardened database-layer multi-tenant workspace isolation across all models and endpoints.
- Added Settings API endpoints in `app/api/v1/settings.py`:
  - `GET`/`PUT /api/v1/settings/workspace-caps`: configure cell caps, place caps, daily LLM cost, retention days.
  - `GET`/`PUT`/`POST /api/v1/settings/scoring-weights` and `/reset`: custom weights with 1-click reset to defaults.
  - `GET /api/v1/settings/api-usage`: active spend vs cap metrics.
- Added Account tools in `app/api/v1/account.py`:
  - `GET /api/v1/account/export`: streaming full account data as JSON or CSV.
  - `DELETE /api/v1/account/data`: irreversible cascade deletion with strict "DELETE MY DATA" confirmation.
- Built comprehensive tabbed Settings page at `apps/web/app/settings/page.tsx` (Offer Profile, Scoring Weights, Workspace Caps, API Usage, Account Security, Data Export, Delete Data).
- Added comprehensive test suite in `tests/test_auth_tenancy.py` (5 tests passing) verifying email verification, password reset, cross-tenant isolation enforcement, workspace caps, and export/deletion.

### 2026-11-20 - Prompt 15: Model insights and active learning
- Added active learning and ranking comparison endpoints in `app/api/v1/models.py`:
  - `GET /api/v1/models/active-learning`: prioritizes decision-boundary uncertain leads (0.35-0.65 likelihood) and high-opportunity thin-evidence leads.
  - `GET /api/v1/models/ranking-comparison`: returns side-by-side comparison of rule-only rank vs model-blended rank for top 20 leads with rank shift indicators.
- Built Model Insights page at `apps/web/app/models/page.tsx`:
  - Active model status, algorithm, training timestamp, and sample size.
  - KPI metric cards: ROC-AUC (vs 0.70 benchmark), PR-AUC, Precision@10 with lift over rules, and Brier calibration loss.
  - Interactive SVG ROC Curve and Calibration Reliability plots.
  - Feature-importance horizontal bar charts showing signal weights.
  - Full model version history table with one-click rollback functionality.
  - Honest cold-start empty state explaining rule-based ranking and displaying live dataset health progress toward ML unlock.
- Built Active-Learning Queue at `apps/web/app/leads/active-learning/page.tsx`:
  - Prioritizes uncertain and thin-evidence candidates to maximize training information gain.
  - Added shortcut link on Leads page header.
- Implemented 'Why this score' panel in `apps/web/components/leads/lead-drawer.tsx`:
  - Combines 5-component rule breakdown and SHAP top feature contributions in plain English with impact direction badges.
- Updated main navigation in `apps/web/components/navbar.tsx` with ML Model link.
- Added comprehensive unit tests in `tests/test_ml.py` verifying active-learning prioritization and ranking comparison endpoint calculations (324 passed).

### 2026-11-20 - Prompt 14: ML training pipeline
- Implemented cold-start gating in `app/ml/gating.py`:
  - Enforces minimum 150 labelled outcomes and 20 positive replies before ML unlocking.
  - Transparently explains required remaining counts while in rules-only mode.
- Implemented ML training tournament in `app/ml/pipeline.py`:
  - Extracts 19 numeric features and handles missing values with explicit median imputation.
  - Trains standardized regularized `LogisticRegression` baseline with Platt scaling (`CalibratedClassifierCV`).
  - Trains gradient-boosted `HistGradientBoostingClassifier` challenger with probability calibration.
  - Performs time-based temporal splitting when sufficient chronological samples exist (stratified split fallback).
  - Evaluates models on ROC-AUC, PR-AUC, Brier score, and precision@10.
  - Selects the winning model based on validation ROC-AUC.
- Implemented dynamic rule + ML blending in `app/ml/blending.py`:
  - Configurable blend function scaling model weight smoothly from 0.30 at 150 samples to 0.80 at 1000+ samples.
- Implemented SHAP explainability engine in `app/ml/shap_explainer.py`:
  - Extracts top 3 feature impacts and plain-English reasons per lead for explainable ranking.
- Implemented model registry and safe rollout in `app/ml/registry.py`:
  - Persists artifacts to disk, logs metrics to `model_versions`, and automatically activates challenger only if it outperforms current model.
  - Added one-click rollback function (`rollback_model_version`).
- Implemented automated retraining Celery task in `app/tasks.py`:
  - `retrain_workspace_models_task`: checks if 25+ new labelled outcomes exist; skips if a scrape job is active.
- Implemented feature distribution drift check in `app/ml/drift.py`:
  - Flags shifts exceeding 2.0 standard deviations between inference leads and training baselines.
- Connected API endpoints in `app/api/v1/models.py`:
  - `POST /api/v1/models/train` (runs tournament, supports force parameter)
  - `POST /api/v1/models/{version_id}/rollback` (one-click rollback)
  - `GET /api/v1/models/leads/{lead_id}/explanation` (SHAP top-3 contributions)
- Added comprehensive test suite in `tests/test_ml.py` (6 tests passing):
  - Verified cold-start gating logic.
  - Verified planted signal recovery on synthetic data: model achieves ROC-AUC >= 0.70 and precision@10 >= 0.50.
  - Verified rule + ML blending weight progression.
  - Verified tournament activation rules and one-click rollback.
  - Verified SHAP top-3 explanation generation.
  - Verified feature distribution drift warnings.

### 2026-11-20 - Prompt 13: Outcome logging and dataset builder
- Implemented outcome logging and CSV importer in `app/outcomes/logging.py`:
  - Quick logging of `replied`, `no_reply`, `meeting`, `converted` outcomes in `outreach_events`.
  - Auto-updates lead status and appends internal outcome notes.
  - CSV batch importer (`import_outcomes_from_csv`) matching by email, domain, or place name.
- Implemented 14-day outreach window-closing Celery task in `app/tasks.py`:
  - Scheduled daily via Celery beat (`close-outreach-windows-daily`).
  - Closes overdue contacted leads older than 14 days without replies, creating a `no_reply` event.
- Built leak-free training dataset builder in `app/outcomes/dataset.py`:
  - Enforces zero data leakage: reads strictly from frozen `features_snapshot` in `contacted` events.
  - Formulates labels: `label = 1` for replies <= 14 days; `label = 0` for `no_reply` or > 14 days without reply.
  - Excludes open windows (< 14 days with no reply) and DNC / opt-out leads.
  - Provides `get_dataset_health` calculating volume, positive rate, and cold-start unlocking delta.
- Added API endpoints in `app/api/v1/leads.py` and `app/api/v1/models.py`:
  - `POST /api/v1/leads/{id}/outcomes`
  - `POST /api/v1/leads/outcomes/import-csv`
  - `GET /api/v1/models/dataset/health`
  - `GET /api/v1/models/dataset/export`
- Built frontend UI:
  - `apps/web/components/dataset-health-card.tsx` displaying labelled count, positives, reply rate, and progress bar toward ML unlock.
  - Embedded health card in `apps/web/app/leads/page.tsx`.
  - Added Quick Log Outcome action bar (Replied, Meeting, Converted, No Reply) in `apps/web/components/leads/lead-drawer.tsx`.
- Added unit and anti-leakage test suite in `tests/test_outcomes.py` (4 tests passing):
  - Verified snapshot immutability: proved post-contact mutations to `Place` or `LeadFeature` do NOT alter training row.
  - Verified window closing Celery task: overdue leads auto-closed, active windows preserved.
  - Verified CSV outcome import and status updates.
  - Verified dataset health and cold-start gating logic.

### 2026-11-20 - Prompt 12: Outreach workflow
- Built DNC management in `app/services/dnc.py`, `app/schemas/dnc.py`, and `app/api/v1/dnc.py`:
  - Contact lookup (`is_contact_dnc`, `is_lead_dnc`) and creation (`add_to_dnc`) by email, domain, or phone.
  - Excludes DNC leads from default leads list queries (`include_dnc=False`).
  - Automatically registers business contact vectors on DNC when lead status is set to `do_not_contact`.
- Built grounded draft generator in `app/services/drafts.py`:
  - Enforces channel length caps: WhatsApp / chat <= 450 characters; cold email <= 120 words.
  - Enforces mandatory opt-out lines: "Reply STOP to opt out." for chat; "Reply STOP or unsubscribe to not hear from us again." for email.
  - Selects exactly one verified finding without hallucinated metrics (falls back to clean place facts or `[N]`).
  - Supports Claude API structured generation with robust deterministic fallback.
  - Constructs zero-automation `mailto:` and `https://wa.me/` deep links.
- Updated leads API in `app/api/v1/leads.py`:
  - Added `POST /api/v1/leads/{id}/generate-draft` with DNC blocking (`DNCBlockedError` -> HTTP 400).
  - Enforced status transition validation in `PATCH /api/v1/leads/{id}`.
  - Automatically captures and freezes `features_snapshot` in `outreach_events` upon transitioning to `contacted`.
- Built Next.js leads management UI:
  - Scored leads table at `apps/web/app/leads/page.tsx` with sorting, multi-select, and quick filters (status, min score, has email, DNC toggle).
  - Bulk actions for Shortlist and Reject.
  - Interactive lead drawer `apps/web/components/leads/lead-drawer.tsx` with business facts, 5-component score breakdown, internal notes editor, status pipeline selector, and event timeline.
  - Draft generator component `apps/web/components/leads/draft-generator.tsx` with channel switch, tone select, live word/char counters, editable draft area, Copy button, "Open in Mail", "Open WhatsApp", and "Mark as Contacted" button.
  - Added Leads page link to main navigation `apps/web/components/navbar.tsx`.
- Added test suite in `tests/test_outreach.py` (5 tests passing):
  - Verified chat (<= 450 chars) and email (<= 120 words) length caps and mandatory opt-out lines.
  - Verified grounded citations and non-hallucinated fallbacks.
  - Verified DNC blocking of drafts and status transitions.
  - Verified automatic feature snapshotting on `contacted`.
  - Proved non-negotiable safety: verified zero automated sending code paths exist.

### 2026-11-20 - Prompt 11: LLM enrichment
- Added `LLMUsageLog` model in `app/models.py` and created new Alembic migration `01ba234950a3_add_llm_usage_logs_table.py` (`down_revision = 'd70954e45f7b'`).
- Added LLM settings in `app/config.py`: `anthropic_api_key`, `llm_model_fast` (default `claude-3-5-haiku-20241022`), `llm_model_quality` (default `claude-3-5-sonnet-20241022`), and `llm_daily_cost_cap_usd` (default $2.00).
- Implemented safe website fetcher with strict SSRF defense in `app/enrichment/safe_fetcher.py`:
  - Blocks private, loopback, link-local, multicast, and cloud metadata IP ranges (including redirects).
  - Enforces 512 KB size limit and 8s timeout.
  - Computes deterministic web signals (HTTPS, mobile viewport meta tag, load time, contact forms, booking links, social links) and extracts clean body text.
- Implemented workspace daily cost tracking and cap enforcement in `app/enrichment/cost_guard.py`: tracks prompt/completion tokens, logs usage in `llm_usage_logs`, and raises `CostCapExceededError` if the workspace's daily spending limit is reached.
- Implemented `AnthropicClient` in `app/enrichment/anthropic_client.py`:
  - Enforces prompt injection protection: wraps untrusted scraped text in `<untrusted_scraped_data>...</untrusted_scraped_data>` tags and instructs the model never to execute embedded instructions.
  - Validates structured JSON responses using Pydantic schemas with automatic 1-attempt retry on invalid JSON and graceful error handling.
  - Provides deterministic local fallback generation when running without API keys.
- Implemented website audit module in `app/enrichment/website.py`: evaluates value clarity, CTA effectiveness, mobile readiness, top issues, and overall score (0-100), cached by `sha256(content)` in `enrichments` table and updates `lead_features.features["website_audit_score"]`.
- Implemented review themes extraction module in `app/enrichment/reviews.py`: analyzes up to 30 recent customer reviews to extract recurring complaints, praises, owner response behavior, and a high-converting one-line pitch angle; cached by content hash and updates `lead_features.features["number_of_review_pain_themes"]`.
- Implemented orchestration pipeline in `app/enrichment/pipeline.py` and wired Celery tasks `enrich_lead_task` and `enrich_job_leads_task` in `app/tasks.py`.
- Added comprehensive unit and integration test suite in `tests/test_enrichment.py`:
  - SSRF defense verification blocking private/loopback IPs.
  - Deterministic HTML signal extraction.
  - JSON schema parsing and retry on malformed JSON.
  - Content-hash caching verifying second runs hit cache with 0 LLM calls.
  - Daily cost cap enforcement verifying spending halts gracefully when cap is reached.
- Verified: All 308 API pytest tests passing in 8.91s; `ruff check` and `ruff format` clean; `alembic check` clean with zero drift.
- Commit: `feat(enrichment): website audit and review themes`.

### 2026-11-20 - Prompt 10: Lead features and rule-based scorer
- Added `OfferProfile` model in `app/models.py` and created new Alembic migration `d70954e45f7b_add_offer_profiles_table.py` (`down_revision = '9806193c2e18'`).
- Created `config/scoring.yaml` and loader `app/scoring/config.py` defining 5 component weights (Pain: 25.0, Fit: 25.0, Timing: 15.0, Reachability: 20.0, Evidence: 15.0) and thresholds.
- Built lead feature extraction pipeline in `app/scoring/features.py` (version `v1`): extracts 20 deterministic, review, and neighborhood features (rating, review count, log_review_count, has_real_website, website_is_https, has_phone, has_named_email, has_generic_email, price_level, hours_complete, owner_reply_rate, negative_review_share, days_since_last_review, hex_opportunity_score, hex_supply_count, hex_demand_proxy, distance_to_nearest_competitor_m, plus website_audit_score and number_of_review_pain_themes placeholders).
- Built rule-based cold-start scoring engine in `app/scoring/rules.py`: computes transparent 0-100 scores across Pain, Fit, Timing, Reachability, and Evidence, producing a structured, readable `score_breakdown` JSON with points and clear explanatory reasons.
- Built workspace lead scoring pipeline in `app/scoring/pipeline.py`: batch processes places, extracts features, calculates rule scores, and upserts `Lead` and `LeadFeature` records.
- Added Offer Profile REST endpoints in `app/api/v1/offer_profile.py` (`GET` and `PATCH/PUT /api/v1/offer-profile`) and wired them into `app/api/v1/__init__.py`.
- Wired Celery task `score_job_leads_task` in `app/tasks.py` automatically triggered after gap analysis completion.
- Added comprehensive unit and integration tests in `tests/test_scoring.py`:
  - Feature extraction accuracy across place and review metrics.
  - Hand-made leads with obvious expected rankings: High-pain target-matching prospect (score 80+) drastically outscoring an unfit, unreachable prospect (score < 30) by > 40 points.
  - Offer Profile sensitivity: changing target category from `cafe` to `gym` directly modifies Fit component from 25.0 to 0.0.
  - End-to-end database pipeline testing verifying `Lead` and `LeadFeature` rows.
  - Added OpenAPI verification and lifecycle tests for `/api/v1/offer-profile` in `tests/test_api_v1.py`.
- Verified: All 299 API tests passing in 8.53s; `ruff check` and `ruff format` clean; `alembic check` clean with zero drift.
- Commit: `feat(scoring): lead features and rule-based scorer`.

### 2026-11-20 - Prompt 9: Gap map UI
- Installed MapLibre GL, deck.gl, and h3-js: `maplibre-gl` (6.19.0), `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/geo-layers`, `@deck.gl/react`, `@deck.gl/mapbox` (9.4.1), `h3-js` (4.5.0).
- Implemented diverging, color-blind-safe palette (emerald green to amber to coral red) in `apps/web/lib/color-scale.ts` for opportunity score, supply count, density, average rating, and demand proxy with matching dynamic legend indicators.
- Implemented map components:
  - `apps/web/components/map/gap-map.tsx`: MapLibre GL base map using OpenFreeMap liberty vector tiles, deck.gl MapboxOverlay with `H3HexagonLayer` and `ScatterplotLayer` (for place markers), cursor pointer styling, hover tooltip with opportunity score and supply metrics, smooth `flyTo` camera transitions, and canvas snapshot generation via `preserveDrawingBuffer`.
  - `apps/web/components/map/map-controls.tsx`: Floating map toolbar supporting metric switching (Opportunity, Supply, Density, Rating, Demand), opacity slider (0.1 to 1.0), place marker toggle, resolution indicator, dynamic legend scale, and export triggers (PNG snapshot, CSV metrics download, shareable link).
  - `apps/web/components/map/gap-summary-cards.tsx`: Interactive banner featuring top 3 high-opportunity (underserved) and top 3 saturated hexes with fly-to click handlers.
  - `apps/web/components/map/hex-drawer.tsx`: Side drawer revealing comprehensive hex statistics, top 3 explainable gap reasons, and the live paginated list of places situated inside the hex.
- Created `apps/web/app/gap/[id]/page.tsx` integrating map, drawer, summary cards, and controls.
- Added automated tests:
  - Unit component tests in `apps/web/test/gap-map.test.tsx` (6 tests covering color scales, drawer metrics and place rendering, summary cards, and map controls).
  - End-to-end browser test in `tests-e2e/gap-map.spec.ts` testing map rendering, summary cards, control toggles, and side drawer inspection.
- Verified:
  - Vitest: 12 tests passed across 3 test files in 16.7s.
  - TypeScript: `tsc --noEmit` passed with 0 errors.
  - Lint and formatting: ESLint passed with 0 errors; Prettier passed.
  - Playwright: `tests-e2e/gap-map.spec.ts` passed (1 passed in 15.1s).
- Commit: `feat(web): interactive gap map`.

### 2026-11-19 - Prompt 8: Frontend foundation
- Added web dependencies in apps/web/package.json: @tanstack/react-query, lucide-react, vitest, @testing-library/react, @testing-library/jest-dom, jsdom, @vitejs/plugin-react.
- Implemented typed API client and TypeScript models in apps/web/lib/types.ts and apps/web/lib/api.ts for auth, jobs, places, gap analysis, and account data portability/deletion.
- Created QueryClientProvider wrapper in apps/web/components/providers.tsx and responsive persistent navigation in apps/web/components/navbar.tsx.
- Created auth pages:
  - apps/web/app/login/page.tsx: sign in with error banner, loading states, and redirect to dashboard.
  - apps/web/app/register/page.tsx: workspace creation with full name, email, password, and instant onboarding.
- Created jobs management pages:
  - apps/web/app/dashboard/page.tsx: live jobs list table with status badges, progress bars, places count, loading skeletons, and empty state.
  - apps/web/app/jobs/new/page.tsx: analysis form with category dropdown from taxonomy, geocoded area name, cell size slider (500m-3000m), debounced live dry-run grid and runtime/cost estimate, and job creation.
  - apps/web/app/jobs/[id]/page.tsx: live progress polling every 3 seconds, progress bar, cancel/resume controls, post-completion data quality report (open/closed, website, phone, email, rating coverage), and gap summary preview.
  - apps/web/app/settings/page.tsx: user profile, workspace isolation info, DPDP/GDPR JSON data export, and right-to-be-forgotten permanent data deletion.
- Updated landing page apps/web/app/page.tsx with call-to-actions linking to dashboard, new analysis, login, and registration.
- Added component test suite in apps/web/test/:
  - test/job-form.test.tsx: tests form rendering, slider changes, dry run calculation, and job submission redirect.
  - test/job-progress.test.tsx: tests live progress polling, cancellation controls, and completed quality report rendering.
- Verified: All 6 web vitest tests passing in 9.67s; TypeScript tsc --noEmit clean; ESLint clean; Prettier clean; all 294 API pytest tests passing.

### 2026-11-19 - Prompt 7: Backend API
- Added dependencies to apps/api/requirements.txt: argon2-cffi==23.1.0, pyjwt==2.10.1, httpx==0.28.1, email-validator==2.2.0.
- Implemented Argon2id password hashing and short-lived JWT access and rotating refresh tokens in app/auth/security.py.
- Implemented tenant isolation and security dependencies in app/api/deps.py: get_current_user (JWT Bearer authentication), get_current_workspace (guarantees workspace tenant isolation for every operation), and sliding window rate_limiter (120 req/min).
- Implemented RequestIdMiddleware in app/main.py: generates or propagates X-Request-ID across all requests and responses, plus consistent error response format.
- Implemented Pydantic v2 schemas across app/schemas/ for auth, jobs, places, gap analysis, leads, outreach drafts, outreach events, and models.
- Implemented versioned /api/v1 endpoints in app/api/v1/:
  - auth: POST /register, POST /login, POST /refresh, GET /me.
  - jobs: POST /jobs (dry_run=true returns cost and grid estimate; dry_run=false creates job and dispatches cells), GET /jobs (paginated), GET /jobs/{id} (progress polling), POST /jobs/{id}/cancel, POST /jobs/{id}/resume.
  - places: GET /places (filters by category, min_rating, has_website, hex, and text search; cursor pagination).
  - gap: GET /gap/{job_id}/hexes (returns hex metrics and standard GeoJSON FeatureCollection with polygon boundaries), GET /gap/{job_id}/summary (best 3 and saturated 3 hexes).
  - leads: GET /leads (sort by final_score, filter by status, min_score, has_email, hex), GET /leads/{id}, PATCH /leads/{id} (status and notes), POST /leads/{id}/drafts, POST /leads/{id}/events.
  - models: GET /models, GET /models/active/metrics (reports cold-start rules mode), POST /models/train.
  - account: GET /account/export (exports full workspace data as JSON for DPDP/GDPR data portability), DELETE /account/data (right-to-be-forgotten cascading deletion).
- Added comprehensive integration test suite in tests/test_api_v1.py:
  - Validates OpenAPI schema lists every single required endpoint and returns X-Request-ID.
  - End-to-end auth lifecycle: register -> login -> refresh -> /me.
  - Jobs lifecycle: dry run estimate and actual job creation.
  - Strict tenant isolation test: proves User A (Workspace A) data cannot be read, cancelled, or listed by User B (Workspace B).
  - Leads, drafts, events, and account export/deletion tests.
- Verified: 294 tests passed in 9.56s; ruff check and format clean; web eslint and tsc clean.

### 2026-11-19 - Prompt 6: Gap analysis engine
- Created config/gap.yaml and app/gap/config.py with configurable smoothing constant, quality gap weight, k-ring neighbor weight, quantile thresholds, and category-specific anchor weights.
- Implemented anchor category classification in app/gap/anchors.py: identifies offices, colleges, residential apartments, shopping malls, transit stations, and hospitals.
- Implemented explainable market gap engine in app/gap/engine.py:
  - Fast SQL/PostGIS bulk-tuple extraction of workspace places avoiding ORM instantiation overhead for 50k-place scalability.
  - H3 grid indexing and bounding box polygon mapping.
  - Computes per-hex supply count, density per km2, average rating, average review count, quality gap relative to area median, and nearest competitor distance.
  - Calculates demand proxy from anchor categories inside hex and its 1-ring neighbors, with automatic fallback to total business density when anchor data is absent.
  - Applies k-ring (k=1) spatial smoothing to competitor supply.
  - Computes 0-100 opportunity score with quality gap bonus, bounded strictly to [0, 100].
  - Labels hexes using quantile thresholds (underserved, balanced, oversaturated, insufficient_data).
  - Generates top 3 readable explanation reasons per hex and area summary (best 3 and saturated 3 hexes).
  - Upserts HexMetric records into PostgreSQL and saves gap summary to search_jobs.params["gap_summary"].
- Wired Celery compute_gap_analysis_task in app/tasks.py into the post-scrape pipeline (scrape -> clean -> gap).
- Added comprehensive test suite in tests/test_gap.py:
  - Anchor category classification tests.
  - Parametric property tests verifying opportunity score is strictly between 0 and 100 across 240 combinations of supply, demand, and quality gaps.
  - Synthetic city test with crowded downtown centre (10 cafes, rating 3.2, labeled oversaturated) vs empty high-demand suburb (0 cafes, 12 offices, 8 apartments, 3 colleges, 1 transit station, labeled underserved with score >= 70 and top reasons).
- Verified: 288 tests passed in 5.55s; ruff check/format clean; web eslint/tsc clean.

### 2026-11-19 - Prompt 5: Cleaning, normalisation and deduplication
- Switched RUN_MODE in BUILD_PLAN.md to full for continuous execution across remaining prompts.
- Added dependencies to apps/api/requirements.txt: phonenumbers==9.0.43, h3==4.5.1, dnspython==2.9.2.
- Implemented category normalisation in app/cleaning/taxonomy.py: maps messy/raw business categories into controlled taxonomy (cafe, restaurant, gym, salon, dental clinic, coaching centre) via exact token matching and difflib fuzzy matching while retaining the original raw category.
- Implemented phone normalisation in app/cleaning/phone.py: validates and normalises phone numbers to E.164 with +91 as default region using the phonenumbers library; invalid numbers are dropped.
- Implemented website cleaning in app/cleaning/website.py: extracts clean domain, strips tracking query parameters (UTM, gclid, fbclid, etc.), and identifies social-media-only pages (Instagram, Facebook, Linktree, WhatsApp wa.me, etc.) as 'no real website'.
- Implemented email validation and MX checks in app/cleaning/email.py: checks RFC syntax, flags generic mailboxes (info@, contact@, support@, etc.) vs named mailboxes, and performs bounded concurrent domain MX checks with thread-safe caching.
- Implemented duplicate detection and merging in app/cleaning/duplicates.py: detects duplicates within 50m distance and fuzzy name matching (SequenceMatcher >= 0.85 and token containment), absorbs missing fields into the more complete primary record, and marks secondary duplicates with is_closed=True and raw["is_duplicate"]=True.
- Implemented H3 resolution 8 computation in app/cleaning/pipeline.py: calculates h3_r8 for every place with geographic coordinates using h3.latlng_to_cell.
- Implemented data-quality report generation in app/cleaning/pipeline.py: computes total places, open/closed counts, percentage with website, percentage with phone, percentage with email, percentage with named email, rating coverage, and duplicate count; saves report to search_jobs.params["quality_report"].
- Wired Celery clean_and_normalize_places_task into trigger_post_scrape_pipeline in app/tasks.py.
- Added test suite in tests/test_cleaning.py: 10+ messy examples each for category, phone, website, and email normalisation, plus duplicate detection, H3 indexing, and end-to-end database pipeline testing.
- Verified: 46 tests passing in 4.79s; ruff check and format clean; web eslint and tsc clean.


### 2026-11-19 - Prompt 4: Grid planner and job orchestration
- Implemented Nominatim geocoding in app/services/geocoding.py: maps city/area names to bounding boxes with custom User-Agent and in-memory caching.
- Implemented grid planner in app/services/grid.py: divides arbitrary bounding boxes into overlapping search cells with center coordinates, calculates runtime/cost estimates, and enforces workspace safety caps (MAX_CELLS_PER_JOB).
- Implemented job lifecycle and orchestration in app/services/jobs.py: create_search_job (persisting SearchJob and child SearchJobCell records with polygon geometries), pause_search_job, cancel_search_job, resume_search_job, and get_job_progress.
- Implemented Celery tasks in app/tasks.py: scrape_cell_task (cell centroid calculation via PostGIS, places cap check, status tracking, exponential backoff retries, and post-scrape pipeline trigger) and dispatch_job_cells with rate pacing.
- Implemented places deduplication across overlapping cells via upsert_places.
- Added comprehensive test suites:
  - tests/test_grid.py: mathematical full coverage, positive overlap, bounds check, runtime estimation, cap enforcement.
  - tests/test_geocoding.py: caching, parsing, not-found error handling.
  - tests/test_orchestration.py: end-to-end 3x3km grid execution over 16 cells with live progress tracking, pause/resume, cancellation, error recording, and deduplication of central overlapping places (17 total places from 16 cells).
- Verified: 36 passed in 3.93s; ruff check/format and web lint/format/typecheck all green.

### 2026-11-19 - Prompt 3: Data source layer and scraper integration
- Researched gosom/google-maps-scraper REST API (/static/spec/spec.yaml) and CLI flags; documented in /docs/scraper-notes.md (job creation POST /api/v1/jobs, polling GET /api/v1/jobs/{id}, CSV download GET /api/v1/jobs/{id}/download, email/extra-reviews/geo/depth controls, CSV columns).
- Defined DataSourceProvider interface, RawPlace, ReviewDTO, PlaceDTO, and SearchOptions in app/providers/base.py.
- Added stubs for GooglePlacesApiProvider and CsvImportProvider in app/providers/stubs.py with clear TODOs.
- Implemented GosomScraperProvider in app/providers/gosom.py with request logging (omitting proxy secrets), job submission, exponential backoff polling, timeout handling, defensive CSV/JSON parsing (malformed reviews, unicode, missing coordinates, price level symbols), and mapping to PlaceDTO.
- Implemented upsert_places service in app/services/places.py: idempotent upserts keyed by (workspace_id, provider, provider_place_id) storing untouched row in places.raw and child reviews in place_reviews with owner reply detection.
- Implemented CLI command in app/cli.py (`python -m app.cli scrape --category ... --area ...`) to run queries and store results.
- Added 27 tests across test_schema, test_parsing, test_gosom_provider, test_upsert, and test_cli. Shared database fixtures moved to tests/conftest.py.
- Verified:
  - Unit tests: 27 passed in 3.24s.
  - Linters: ruff check and ruff format passed; web eslint, prettier, and tsc passed.
  - Live query: ran `python -u -m app.cli scrape --category "bakery" --area "Indiranagar, Bangalore" --depth 1` against the live scraper service -> found 16 places and upserted them into the database.
  - Idempotency: ran the exact same query a second time against the workspace -> 51 places before, 51 places after, 0 duplicate rows created.
- Decisions and deviations:
  - Scraper REST API returns PascalCase `{"Status": "ok", "ID": "..."}` on completion; GosomScraperProvider was implemented to normalize both uppercase/lowercase keys and handle "ok" / "completed" statuses.
  - Moved session database test fixtures to `tests/conftest.py` so all test modules share the migrated throwaway database without duplicating test harness code.

### 2026-11-19 - Plan refinement & reconciliation
- Patched BUILD_PLAN.md per instructions:
  1. Section 3 Step 2: updated prompt reference to Section 9.
  2. Section 8 Engineering Rules: added rule 10 requiring new Alembic migrations for future database state additions.
  3. Prompt 1: added shm_size: '2gb' to scraper service in infra/docker-compose.yml; updated acceptance criterion to local validation of CI workflow.
  4. Prompt 2: added search_job_cells table definition to support pause/cancel/resume in Prompt 4.
  5. Prompt 5: added MX checks domain caching and bounded concurrency specification.
  6. Prompt 6: specified SQL/PostGIS or bulk tuple/NumPy hex aggregations.
  7. Prompt 7 & 16: clarified Argon2/token rotation/workspace isolation in Prompt 7 and verification/reset/RLS/settings/export in Prompt 16.
  8. Prompt 12: added fallback outreach drafting from lead facts alone if Prompt 11 is skipped.
  9. Appendix 10: updated model references to claude-haiku-<latest> and claude-sonnet-<latest>.
- Reconciled Prompt 1: added `shm_size: '2gb'` to `scraper` in `infra/docker-compose.yml`.
- Reconciled Prompt 2: added `SearchJobCell` model in `apps/api/app/models.py`, created second migration `9806193c2e18_add_search_job_cells_table.py` (`down_revision = '9776c3c292c0'`), updated `apps/api/tests/test_schema.py` with `test_search_job_cells_constraints_and_cascade`.
- Verified: `alembic upgrade head` succeeded, `alembic check` reports zero drift, pytest passes (16 passed in 3.00s), ruff and web lint/format/typecheck all pass.

### 2026-11-19 - Prompt 2: Database schema and migrations
- Added geoalchemy2 0.21 and 13 SQLAlchemy 2 models: workspaces, users, search_jobs, places, place_reviews, hex_metrics, leads, lead_features, enrichments, outreach_drafts, outreach_events, model_versions, do_not_contact.
- Every user-data table carries a non-null workspace_id (users plus all domain tables); a user maps to one workspace for simple tenant isolation.
- Constraints/indexes: unique (workspace_id, provider, provider_place_id) on places; unique (workspace_id, place_id) on leads; unique (workspace_id, kind, content_hash) on enrichments; partial unique active model per workspace; partial unique DNC email/domain/phone; GiST on places.location (and search_jobs.bbox); btree (workspace_id, h3_r8), (workspace_id, status), (workspace_id, normalized_category), (workspace_id, website_domain). Statuses are VARCHAR + CHECK constraints, not native enums.
- Alembic: apps/api/alembic.ini and migrations/env.py read DATABASE_URL (tests inject a URL via config.attributes); the initial migration enables PostGIS first; autogenerate excludes extension-owned objects (PostGIS/Tiger).
- Seed: scripts/seed.py upserts a demo workspace and 20 fake Indiranagar places; idempotent via ON CONFLICT.
- Compose: PYTHONPATH=/app for Python services so /scripts/seed.py can import the app package.
- Run: `make up`, `make migrate`, `make seed`.
- Test: `make test` -> 15 passed. The suite creates/migrates/downgrades/drops a throwaway `<db>_test` database and checks the table set, workspace_id on every user-data table, uniqueness, CHECKs, partial indexes and a 1 km ST_DWithin query. `make lint` passes (ruff now covers migrations and scripts).
- Verified: upgrade -> downgrade base -> upgrade; `alembic check` reports no drift; seed run twice -> 20 places; /health ok (db 1.07 ms, redis 2.59 ms); all 7 containers healthy/running.
- Decisions/deviations:
  - Child tables (place_reviews, lead_features, enrichments, outreach_drafts, outreach_events) also carry workspace_id, per "every row of user data carries a workspace_id"; this keeps Prompt 16 isolation direct.
  - GeoAlchemy2 creates GiST indexes during CREATE TABLE, so duplicate generated create/drop index calls were removed. The auto-created bbox GiST index on search_jobs is kept for Prompt 4 bbox queries.
  - The PostGIS image installs Tiger geocoder tables in public; env.py excludes all extension-owned relations so migrations never drop them.
  - env.py ends the read transaction opened while listing extension tables; without that, Alembic's migration DDL was rolled back silently.
  - Seed emails/websites use reserved example domains; all seed data is clearly fake.

### 2026-11-19 - Prompt 1: Repo scaffold and dev environment
Plan: monorepo layout; compose with 7 services and healthchecks; FastAPI /health (db+redis); Celery ping; Next.js page polling /health; Makefile; env reference; lint/format configs; CI.
- Created apps/api (FastAPI 0.165, SQLAlchemy 2.1, psycopg 3, Celery 5.7, pydantic-settings), apps/web (Next 16.4 App Router, React 19.3, Tailwind 4.3, strict TS), infra/docker-compose.yml, scripts/seed.py, tests-e2e, docs, Makefile, .env.example, pre-commit, GitHub Actions.
- Scraper service runs gosom/google-maps-scraper with `-web -addr :8080 -data-folder /gmapsdata`; image facts taken from its current README.
- Run: `make up` (no .env required; compose has dev defaults), then open http://localhost:3000, http://localhost:8000/docs, http://localhost:8080.
- Test: `make test` -> 5 passed; `make lint` -> ruff check/format, eslint, prettier, tsc all pass; Celery ping -> pong; /health -> {"status":"ok","checks":{"db":{"status":"ok","latency_ms":1.07},"redis":{"status":"ok","latency_ms":2.55}}}.
- Web page verified in a real browser: "All systems operational", Db ok 1.05 ms, Redis ok 2.42 ms.
- Decisions/deviations:
  - Windows 11 host: GNU Make 4.4.1 installed via winget (ezwinports.make); commands run through PowerShell. Compose services are Linux containers.
  - Application Control blocks SQLAlchemy's compiled DLL on the host, so pytest/ruff run in the api container (Python 3.11) rather than a host venv. This matches CI's Python 3.11.
  - ESLint pinned to 10.15.0 (9.39 is deprecated; eslint-config-next 16 accepts >=9). npm prints peer warnings from its bundled eslint-plugin-import but lint passes.
  - Scraper healthcheck uses `bash -c 'exec 3<>/dev/tcp/127.0.0.1/8080'` because the image has neither wget nor curl.
  - `make migrate` is wired to `alembic upgrade head`; it becomes usable with Prompt 2's alembic.ini and migrations. `make seed` currently prints an honest placeholder.
  - LLM model IDs in .env.example are placeholders to be confirmed against Anthropic docs in Prompt 11.
- CI: workflow .github/workflows/ci.yml runs api lint+format+tests and web lint+format+types+build. Its exact steps pass locally; the remote green check needs a GitHub remote (see Blockers).

### 2026-11-19 - Bootstrap
- Verified tools: git 2.56.0, Docker 29.9.3 + Compose v5.7.0 (linux containers), Node v24.21.0, Python 3.12.10 + pip 25.0.1, GNU Make 4.4.1.
- Created AGENTS.md (Section 6 verbatim), CLAUDE.md, GEMINI.md, PROGRESS.md (Section 7 verbatim).
- Settings: RUN_MODE=checkpoints, BUILD_PATH=portfolio, DEPLOY_TARGET=A.
- Deviation: host is Windows 11, not Linux. Commands are run through PowerShell; GNU Make installed via winget (ezwinports.make) and lives on the user PATH. Compose services stay Linux containers.
- Blockers: none.

## Blockers
(anything that needs the human: credentials, installs, decisions)

- Later, not yet needed: ANTHROPIC_API_KEY (Prompt 11) and map tile provider choice (Prompt 9).
