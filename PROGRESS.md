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
- [ ] Prompt 8: Frontend foundation
- [ ] Prompt 9: Gap map UI
- [ ] Prompt 10: Lead features and rule-based scorer
- [ ] Prompt 11: LLM enrichment
- [ ] Prompt 12: Outreach workflow
- [ ] Prompt 13: Outcome logging and dataset builder
- [ ] Prompt 14: ML training pipeline
- [ ] Prompt 15: Model insights and active learning
- [ ] Prompt 16: Auth, tenancy and settings
- [ ] Prompt 17: Compliance and security hardening
- [ ] Prompt 18: Testing and quality
- [ ] Prompt 19: Observability and operations
- [ ] Prompt 20: Deployment and CI/CD
- [ ] Prompt 21: Demo data, docs and portfolio packaging

## Log
(newest first. For each finished prompt: date, what changed, how to run, how to test, decisions and deviations)

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
