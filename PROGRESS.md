# GapScout build progress

Settings are in BUILD_PLAN.md (RUN_MODE, BUILD_PATH, DEPLOY_TARGET).

## Checklist
- [x] Bootstrap (project files created, tools verified)
- [x] Prompt 1: Repo scaffold and dev environment
- [x] Prompt 2: Database schema and migrations
- [x] Prompt 3: Data source layer and scraper integration
- [ ] Prompt 4: Grid planner and job orchestration
- [ ] Prompt 5: Cleaning, normalisation and deduplication
- [ ] Prompt 6: Gap analysis engine
- [ ] Prompt 7: Backend API
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
