# GapScout

[![Version](https://img.shields.io/badge/version-v0.1.0--beta-blue.svg)](https://github.com/kamalnathmallick/GapScout/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-16.4-black.svg)](https://nextjs.org/)

Map-based local market intelligence and sales prospecting platform. GapScout models local business saturation and underserved opportunities on an Uber H3 hexagonal spatial grid, then scores and enriches high-conversion commercial leads for B2B outreach.

---

## About GapScout

GapScout bridges geographic spatial intelligence and automated B2B sales development. Traditional lead scraping tools provide lists without geographic context; GapScout computes competitive density, anchor demand proxies, and market opportunity scores across hexagonal neighborhood cells. 

Every hex's opportunity score acts as a direct feature for ranking commercial prospects. GapScout analyzes visible operational deficiencies (website quality, review dissatisfaction, contact routes), aligns them against user Offer Profiles, and automates AI-powered storefront audits and review themes with strict safety boundaries and daily cost caps.

---

## Key Capabilities (v0.1.0-beta)

- **Interactive Hex Gap Map (MapLibre GL + deck.gl):**
  - Renders multi-resolution Uber H3 hexagonal layers over OpenFreeMap vector tiles.
  - Diverging color-blind-safe visualization across opportunity score, supply, density, ratings, and demand.
  - Interactive top-opportunity and saturated summary cards with camera fly-to animations.
  - Slide-out drawer displaying explainable gap factors and underlying place directories.
  - High-resolution map PNG capture and CSV metrics export.

- **Resumable Scraper Orchestration & Grid Planner:**
  - Automated bounding box cell decomposition with geocoding.
  - Multi-worker Celery task queue with automatic exponential retries.
  - Phone validation to E.164, website cleaning, tracking tag removal, and MX record verification.
  - Spatial duplicate detection and attribute merging within 50m tolerance.

- **Explainable Lead Scoring Engine:**
  - 20 versioned deterministic, review, and neighborhood features per business.
  - Transparent 0–100 cold-start rule scoring covering Pain, Fit, Timing, Reachability, and Evidence.
  - Customizable workspace Offer Profiles (target categories, rating bands, geographic territories).
  - Detailed score breakdown JSON detailing exact rationale and point attributions.

- **AI-Powered Storefront & Review Enrichment:**
  - Hardened website fetcher with strict SSRF defense (blocking private, loopback, and metadata IPs).
  - Deterministic signal extraction: SSL, viewport responsiveness, contact forms, booking links, and social presences.
  - Claude-driven storefront evaluations and customer review theme extraction.
  - Content-hash SHA-256 caching preventing redundant token spend.
  - Automated workspace daily budget tracking and hard cost-cap enforcement.

---

## Architecture & Technology Stack

| Tier | Technologies |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, MapLibre GL, deck.gl, TanStack React Query, Lucide Icons |
| **Backend API** | FastAPI, SQLAlchemy 2 (async/sync), Pydantic v2, GeoAlchemy2, Uvicorn |
| **Database & GIS** | PostgreSQL 16 + PostGIS extension, Uber H3 Spatial Indexing |
| **Async Task Pipeline** | Redis 7, Celery 5.7 (distributed worker & beat scheduler) |
| **Data Scraping** | Gosom Google Maps Scraper (headless Chromium in Docker) |
| **AI & LLM Services** | Anthropic Claude API (structured outputs with safety delimiters) |
| **DevOps & Testing** | Docker Compose, Pytest (308 passing tests), Playwright E2E, Ruff, ESLint, Prettier |

---

## Quick Start

### 1. Prerequisites
- Docker Desktop with Linux containers enabled.
- GNU Make (`winget install --id ezwinports.make -e` on Windows).
- Node.js 20+ and Python 3.11+ (for local host development).

### 2. Launch Local Environment
```bash
git clone https://github.com/kamalnathmallick/GapScout.git
cd GapScout

# Spin up all services (database, redis, api, worker, beat, scraper, web)
make up
```

### 3. Service Dashboard

| Service | Address |
|---|---|
| **Web Dashboard** | [http://localhost:3000](http://localhost:3000) |
| **FastAPI Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **System Health Check** | [http://localhost:8000/health](http://localhost:8000/health) |
| **Scraper Interface** | [http://localhost:8080](http://localhost:8080) |
| **PostgreSQL Database** | `localhost:5432` (`gapscout` / `gapscout`) |

---

## Testing & Verification

Run the test suite across both frontend and backend services:

```bash
# Run backend pytest suite inside API container (308 passing tests)
make test

# Run code style, typing, and lint checks
make lint

# Run web unit tests (Vitest)
npm --prefix apps/web test

# Run browser end-to-end tests (Playwright)
npx --prefix tests-e2e playwright test
```

---

## License

This project is licensed under the permissive terms of the [MIT License](LICENSE).
