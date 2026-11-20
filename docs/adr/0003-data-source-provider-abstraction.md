# ADR 0003: DataSourceProvider Abstraction Layer

## Status
Accepted

## Context
Market intelligence systems depend on local point-of-interest (POI) and place data. Different environments require different data collection backends:
- Local development & testing: Mock datasets and CSV fixtures.
- Autonomous low-cost scraping: Containerized open-source scraper (`gosom/google-maps-scraper`).
- Enterprise production: Official Google Places API (New) or Mapbox Search API.

Coupling downstream cleaning, deduplication, and scoring directly to a specific scraper format would create vendor lock-in and brittle failure modes.

## Decision
We implemented a strict abstract base provider interface: `DataSourceProvider`.
```python
class DataSourceProvider(ABC):
    @abstractmethod
    async def fetch_places(self, query: str, bbox: BoundingBox, depth: int) -> list[PlaceDTO]:
        ...
```
All ingestion pipelines interact exclusively with `PlaceDTO` objects (containing standardized coordinates, name, categories, ratings, reviews, opening hours, and raw payloads). Specific implementations (`GosomScraperProvider`, `FakeScraperProvider`, `GooglePlacesAPIProvider`) encapsulate HTTP calls, rate limiting, and dialect-specific parsing.

## Consequences & Trade-offs
### Advantages:
- **Zero Ingestion Vendor Lock-in:** The entire data ingestion backend can be swapped in one configuration line (`PROVIDER_NAME`).
- **Bulletproof Contract Testing:** Scraper responses are captured as deterministic CSV/JSON fixtures, allowing regression and fuzz tests without network dependencies.
- **Resilience:** Scraper breaking changes do not propagate into database models or business logic.
