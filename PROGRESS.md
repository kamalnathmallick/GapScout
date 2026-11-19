# GapScout build progress

Settings are in BUILD_PLAN.md (RUN_MODE, BUILD_PATH, DEPLOY_TARGET).

## Checklist
- [x] Bootstrap (project files created, tools verified)
- [x] Prompt 1: Repo scaffold and dev environment
- [ ] Prompt 2: Database schema and migrations
- [ ] Prompt 3: Data source layer and scraper integration
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

- CI green check: the repo has no GitHub remote. Create an empty GitHub repo and give me the URL (or add it with `git remote add origin ...`), then push. Until then the workflow is written and its steps pass locally.
- Later, not yet needed: ANTHROPIC_API_KEY (Prompt 11) and map tile provider choice (Prompt 9).
