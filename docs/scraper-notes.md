# gosom/google-maps-scraper: Architecture and Integration Notes

This document summarizes the findings from the `gosom/google-maps-scraper` documentation, CLI flags, OpenAPI 3.0 specification (`/static/spec/spec.yaml`), and web server endpoints running in the Docker container.

## 1. REST API Architecture

When running in web server mode (`-web -addr :8080`), the service exposes an OpenAPI 3.0 compliant REST API:

- **Create Job**: `POST /api/v1/jobs`
  - **Payload (`ApiScrapeRequest`)**:
    ```json
    {
      "name": "Cafes in Indiranagar",
      "keywords": ["cafes in Indiranagar, Bengaluru"],
      "lang": "en",
      "zoom": 15,
      "lat": "12.9784",
      "lon": "77.6408",
      "radius": 5000,
      "depth": 1,
      "fast_mode": false,
      "email": true,
      "max_time": 600,
      "proxies": []
    }
    ```
  - **Response**: `201 Created` with `{"id": "<uuid>"}`.
- **Poll Job Status**: `GET /api/v1/jobs/{id}`
  - **Response**: `200 OK` with:
    ```json
    {
      "id": "<uuid>",
      "name": "...",
      "date": "2026-11-19T...",
      "status": "pending" | "running" | "completed" | "failed",
      "data": { ... }
    }
    ```
- **Download Results**: `GET /api/v1/jobs/{id}/download`
  - **Response**: `200 OK` with content type `text/csv` containing the scraped places and reviews.
- **Delete Job**: `DELETE /api/v1/jobs/{id}`
  - **Response**: `200 OK`.

## 2. CLI Flags and Operational Controls

- **Email Extraction**:
  - Controlled by `-email` CLI flag and `"email": true` in the API payload.
  - When enabled, visits business websites and extracts visible email addresses.
- **Extra Reviews**:
  - Controlled by `-extra-reviews` CLI flag.
  - Anonymously collects additional customer reviews beyond the primary summary.
- **Language**:
  - Controlled by `-lang <code>` (default `"en"`). Sets Google Maps locale interface.
- **Depth**:
  - Controlled by `-depth <int>` (default `10`). Specifies the maximum scroll depth in search results.
- **Coordinates & Zoom**:
  - Coordinates: `-geo "lat,lon"` in CLI or `"lat"`, `"lon"` in API request.
  - Zoom: `-zoom <int>` (0–21, default `15`).
  - Radius: `-radius <float>` (meters, default `10000`).
- **Proxies**:
  - `-proxies "url1,url2"` in CLI or `"proxies": ["..."]` in API payload. Supports HTTP, HTTPS, and SOCKS5 proxies.

## 3. Output Schema (CSV Columns)

The scraper output CSV contains the following fields:
- `input_id`: Correlation ID for the input query
- `link`: Google Maps URL
- `title`: Business name
- `category`: Primary category string
- `address`: Full address text
- `open_hours`: JSON dictionary of operating hours by day
- `popular_times`: JSON dictionary of peak times
- `website`: Website URL
- `phone`: Raw phone string
- `plus_code`: Google Plus code
- `review_count`: Total number of reviews (integer)
- `review_rating`: Average rating (float)
- `reviews_per_rating`: JSON distribution of star ratings (e.g., `{"1": 10, "5": 100}`)
- `latitude`, `longitude`: Decimal coordinates (float)
- `cid`: Google Customer ID
- `status`: Operational status (e.g., "Operational", "Permanently Closed")
- `descriptions`: Short business description
- `reviews_link`: Direct link to Google reviews
- `thumbnail`: Image URL
- `timezone`: Local timezone (e.g. `Asia/Calcutta`)
- `price_range`: Price indicator (e.g., `₹₹`, `$$`)
- `data_id`: Google data identifier (e.g., `0x3bae17dd...`)
- `street_view_url`: Direct link to street view
- `place_id`: Google Place ID (e.g., `ChIJu3MeVd0XrjsRej9BlCg4hv4`)
- `images`: JSON list of image URLs
- `reservations`, `order_online`, `menu`: Links / services
- `owner`: JSON object with owner ID and profile link
- `complete_address`: JSON breakdown of street, borough, city, postal_code, state, country
- `about`: JSON breakdown of accessibility, amenities, etc.
- `user_reviews`: JSON array of review objects (`Name`, `Rating`, `Description`, `When`, etc.)
- `emails`: JSON list of extracted email addresses

## 4. Integration Strategy

1. **Defensive Parsing**:
   - Fields containing JSON (`user_reviews`, `open_hours`, `emails`, `complete_address`) may be null, empty, or have unescaped quotes/unicode.
   - Fall back gracefully to empty lists/dicts on parsing failure.
2. **Provider Keying**:
   - `provider`: `"gosom"`
   - `provider_place_id`: `place_id` (Google Place ID `ChIJ...`) or fallback to `cid` / `data_id` if missing.
3. **Idempotency**:
   - Upsert uses `(workspace_id, provider, provider_place_id)`.
   - Raw untouched CSV row stored as dictionary in `places.raw`.
