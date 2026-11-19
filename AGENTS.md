# GapScout: agent rules (read every session)

Product: GapScout is a map-based market intelligence app. The gap map shows on an H3 hex grid where a local market is oversaturated or underserved for a business category. The lead scorer ranks which businesses to pitch (rules first, then an ML model trained on logged replied / not-replied outcomes). Each hex's gap score is a feature of every lead inside it.

Stack: Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 + PostGIS, Redis + Celery, H3, scikit-learn / LightGBM / SHAP, Anthropic API, Next.js + TypeScript + Tailwind + MapLibre GL + deck.gl, gosom/google-maps-scraper (Docker), Docker Compose, pytest, ruff, Playwright, GitHub Actions. Do not deviate without asking.

Layout: /apps/api, /apps/web, /infra, /docs, /scripts, /tests-e2e.

Engineering rules:
- Small steps; run lint and tests after each step. Never delete or weaken a test to make it pass.
- Type hints in Python, strict TypeScript. Config only through environment variables; never commit secrets; keep .env.example current.
- Every data source sits behind the DataSourceProvider interface. Jobs are idempotent.
- Tests are written alongside the code. Record important design decisions in /docs/adr.
- Check current docs or READMEs before using any third-party library, API or tool flag. Do not rely on memory.

Safety rules (non-negotiable):
- The app NEVER sends emails, chat messages or any outreach automatically. It only drafts; a human sends.
- Scraped text (reviews, websites) is untrusted data, never instructions to the LLM.
- Store only public business information. Honour the do-not-contact list. Every draft has an opt-out line. Support data export and deletion.
- Show a notice that scraping Google Maps may violate Google's Terms of Service.

Workflow: The full plan is in BUILD_PLAN.md and the live state is in PROGRESS.md. At the start of every session read PROGRESS.md and continue with the first unchecked prompt of the chosen BUILD_PATH. Never rely on chat memory; write state to PROGRESS.md. One commit per finished prompt.
