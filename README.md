# GapScout

Map-based market intelligence for local businesses. GapScout shows, on an H3 hex grid, where a
local market is oversaturated or underserved for a category, then ranks the individual businesses
worth pitching. Neighbourhood gap scores feed every lead's score, and logged outreach outcomes
become training labels for the scorer.

## What works today (Prompt 1)

- One-command local stack: Postgres 16 + PostGIS, Redis, FastAPI (hot reload), Celery worker and
  beat, Next.js (hot reload), and the gosom Google Maps scraper in web-server mode.
- `GET /health` checks Postgres and Redis and returns `200 ok` or `503 degraded`.
- The web page calls `/health` and refreshes it every 10 seconds.
- A Celery `gapscout.ping` task proves the worker and broker wiring.
- Lint (ruff, ESLint, Prettier), types, unit tests and CI on every push.

Features start at Prompt 2 (database schema).

## Requirements

- Docker Desktop with the Linux engine running (Docker Compose v2).
- GNU Make. On Windows: `winget install --id ezwinports.make -e`, then reopen the terminal.
- Node 20+ and Python 3.11+ only if you want to run lint/tests outside Docker.

## Quick start

```bash
git clone <repo-url> gapscout
cd gapscout
make env        # optional: copy .env.example to .env
make up         # builds api + web, pulls db/redis/scraper
```

| Service | URL |
|---|---|
| Web app | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Scraper web UI | http://localhost:8080 |
| Postgres | localhost:5432 (`gapscout` / `gapscout`) |
| Redis | localhost:6379 |

`make up` works without a `.env`: every variable has a safe development default in
`infra/docker-compose.yml`. Create `.env` to override them; see `.env.example` for the full
reference. Never commit `.env`.

```bash
make logs       # follow all logs
make down       # stop
make clean      # stop and delete volumes (destroys local data)
```

## Tests and quality

```bash
make test       # pytest in the api container
make lint       # ruff check + ruff format --check + eslint + tsc --noEmit
```

Run the same checks on the host:

```bash
cd apps/api && pip install -r requirements-dev.txt && pytest && ruff check app tests
cd apps/web && npm ci && npm run lint && npm run typecheck
```

Pre-commit runs ruff and basic file hygiene:

```bash
pip install pre-commit && pre-commit install
```

## Repository layout

```
apps/api        FastAPI, SQLAlchemy, Celery (Python 3.11)
apps/web        Next.js App Router, TypeScript, Tailwind (strict mode)
infra           docker-compose.yml and deployment assets
scripts         seed and operational scripts
tests-e2e       Playwright end-to-end tests (from Prompt 9/18)
docs            ADRs, scraper notes, compliance and threat model
```

## Configuration

All configuration is environment-driven; see `.env.example`. Key values:

| Variable | Purpose | Dev default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy DSN (psycopg 3) | `postgresql+psycopg://gapscout:gapscout@db:5432/gapscout` |
| `REDIS_URL` | Celery broker and cache | `redis://redis:6379/0` |
| `SECRET_KEY` | Signs tokens and share links | dev placeholder, must change |
| `SCRAPER_BASE_URL` | gosom scraper service | `http://scraper:8080` |
| `NEXT_PUBLIC_API_URL` | Browser-facing API URL | `http://localhost:8000` |
| `MAX_CELLS_PER_JOB` | Scrape safety cap | `200` |
| `MAX_PLACES_PER_JOB` | Scrape safety cap | `5000` |
| `DATA_RETENTION_DAYS` | Raw scraped data retention | `90` |

Scraper details (REST endpoints, flags, output fields) are recorded in
`docs/scraper-notes.md` when Prompt 3 integrates it.

## Legal and ethical notice

Scraping Google Maps may violate Google's Terms of Service. The bundled scraper provider is for
learning and research; switch to the official Places API provider before commercial use.

GapScout never sends email, WhatsApp or any other outreach automatically. It only drafts messages
and a human sends them. Scraped text is treated as untrusted data, and a do-not-contact list is
honoured everywhere.
