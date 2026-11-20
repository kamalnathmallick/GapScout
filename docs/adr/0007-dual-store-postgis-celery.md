# ADR 0007: Dual Storage Architecture: PostGIS Spatial Engine & Redis/Celery

## Status
Accepted

## Context
Market intelligence operations involve two conflicting workload types:
1. Long-running, I/O-heavy background network scraping and grid tiling (minutes to hours).
2. Sub-second interactive GIS map exploration, multi-layer hex querying, and lead ranking (milliseconds).

Executing heavy grid tiling synchronously within API web workers blocks HTTP request loops and exhausts thread pools. Conversely, decoupling storage into multiple distributed micro-databases increases operational maintenance overhead for small engineering teams.

## Decision
We implemented a **Dual-Engine Architecture with PostgreSQL 16 + PostGIS and Redis + Celery**:
1. **PostgreSQL 16 with PostGIS:** Acts as the single source of truth for all spatial, relational, analytical, and audit state. PostGIS geography types and spatial indexes (`GIST`) accelerate spatial containment queries, nearest-neighbor searches, and H3 coordinate binning.
2. **Redis + Celery (Worker & Beat):** Manages asynchronous distributed job orchestration, grid cell dispatch, retry backoffs, and scheduled maintenance tasks (e.g., 90-day data retention pruning and 14-day outcome window closures).

## Consequences & Trade-offs
### Advantages:
- **Resilience:** If a network failure occurs during a 100-cell scrape job, Celery retries individual cells without losing completed work.
- **Blazing Map Performance:** PostGIS spatial queries return 5,000 hexagonal metrics in < 100ms.
- **Minimal Operational Surface:** Only two backing services (Postgres and Redis) need to be deployed and monitored.
