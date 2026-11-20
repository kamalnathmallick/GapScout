---
name: gapscout-setup
description: Environment setup, Docker verification, database migrations, and Bangalore demo seeding for GapScout.
---

# GapScout Setup Skill

Use this skill to configure, initialize, and verify the GapScout development environment.

## Overview
GapScout runs as a containerized stack with PostgreSQL 16 + PostGIS, Redis, Celery (worker and beat), FastAPI API backend, Next.js frontend, and the open-source Google Maps scraper.

## Quick Start Commands

### 1. Launch Containers
```bash
docker compose up -d
```
Verify all 7 containers are healthy:
`gapscout-api-1`, `gapscout-web-1`, `gapscout-db-1`, `gapscout-redis-1`, `gapscout-worker-1`, `gapscout-beat-1`, `gapscout-scraper-1`.

### 2. Apply Database Migrations
```bash
docker exec gapscout-api-1 alembic upgrade head
```

### 3. Seed Realistic Bangalore Demo Data
```bash
docker exec gapscout-api-1 python ../../scripts/seed_demo.py
```
This populates:
- 180 Bangalore cafes in Indiranagar and Koramangala.
- 23 H3 resolution-8 hex metrics with opportunity scores.
- 180 historical outcome labels (32 positive replies, 148 negatives).
- Automatically triggers the ML tournament and activates the winning model.
- Demo login: `demo@gapscout.test` / `DemoPassword123!`.

### 4. Verify Services
- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
