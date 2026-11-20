# GapScout Threat Model

A concise, single-page threat model covering assets, entry points, trust boundaries, and the top 8 security risks and mitigations across GapScout.

---

## 1. System Overview & Trust Boundaries
- **Untrusted External:** Public websites, Google Maps scraped text, customer review bodies, end-user web inputs.
- **DMZ / Ingress:** Next.js Web App (`:3000`), FastAPI REST API (`:8000`) protected by security middleware.
- **Trusted Internal Network:** PostgreSQL 16 + PostGIS (`:5432`), Redis (`:6379`), Celery worker/beat, Scraper container (`:8080`).

---

## 2. Key Assets
1. **Tenant Data & Intelligence:** Scraped businesses, hex opportunity scores, lead rankings, ML model artifacts, outreach history.
2. **Secrets & Credentials:** Database passwords, JWT secret keys, Anthropic LLM API keys.
3. **Scraper & Outbound Infrastructure:** IP reputation, network egress bandwidth, rate-limit quotas.

---

## 3. Attack Entry Points
- **HTTP API Endpoints:** Authentication, Search Job submission, Settings modification, Data export/deletion.
- **Outbound HTTP Fetchers:** Website audit crawling (`fetch_website_safely`), Geocoding (`Nominatim`).
- **Data Ingestion Pipeline:** Parsing untrusted scrape payloads and customer review text.

---

## 4. Top 8 Risks & Mitigations

| # | Threat / Attack Vector | Impact | Mitigation Strategy |
|---|---|---|---|
| **1** | **Server-Side Request Forgery (SSRF)**<br>Attacker injects internal IP or cloud metadata URL into website auditor. | Host compromise, cloud credential theft (`169.254.169.254`). | Strict IP validation (`safe_fetcher.py`): DNS resolution checks, blocking RFC1918, loopback, multicast, link-local, and cloud metadata IPs; enforces 512KB size cap. |
| **2** | **Prompt Injection via Scraped Data**<br>Malicious review or website content directs LLM to ignore instructions or leak keys. | LLM hijacking, leaked system prompts, hallucinated outputs. | Defensive delimiter tags (`<untrusted_scraped_data>`), Pydantic schema validation, system prompt guardrails, zero execution of untrusted commands. |
| **3** | **Cross-Tenant Data Leakage**<br>Authenticated user from Workspace A queries or modifies Workspace B data. | Data breach, loss of customer trust. | Strict DB-layer workspace filtering (`WHERE workspace_id == current_user.workspace_id`), UUID primary keys, verified isolation test suite (`test_auth_tenancy.py`). |
| **4** | **Google Maps Scraper Throttling & ToS Violations**<br>Aggressive concurrent requests trigger IP blocks or legal notices. | Scraper downtime, IP bans, legal liability. | Mandatory consent checkbox on job creation; randomized polite delays (1.0–2.0s); cell concurrency caps; pluggable official Places API adapter. |
| **5** | **Privacy Violations & Unsolicited Outreach (DPDP / GDPR)**<br>Storing private personal data or contacting opted-out leads. | Regulatory penalties, spam complaints. | Field-level allow-list discarding non-business PII; 90-day raw data retention pruning; hard DNC enforcement; mandatory opt-out lines in drafts; zero auto-send. |
| **6** | **LLM Spend Exhaustion ("Denial of Wallet")**<br>Runaway enrichment loops or adversarial inputs draining API credits. | Financial loss, service suspension. | Per-workspace daily LLM cost caps (`daily_llm_cost_cap_usd`); cost guard checks before inference; model caching via content SHA256 hashes. |
| **7** | **Scraping Job Denial of Service**<br>User requests massive area or fine grid creating millions of cells. | Queue starvation, worker resource exhaustion. | Hard limits on job size (`max_cells_per_job=200`, `max_places_per_job=5000`); dry-run estimation required before job launch. |
| **8** | **Dependency Supply Chain Vulnerability**<br>Compromised third-party Python package or npm module. | Remote code execution, credential exfiltration. | Pinned dependencies; automated dependency vulnerability scanning (`pip-audit`, `npm audit`) in continuous integration (`ci.yml`). |
