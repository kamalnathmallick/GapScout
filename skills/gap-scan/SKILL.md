---
name: gap-scan
description: Scan an area and category to compute H3 hexagonal opportunity and saturation scores.
---

# Gap Scan Skill

Use this skill to initiate a geospatial market analysis job across an area and business category.

## Usage Workflow

### 1. Estimate Grid & Cost
Before launching a scan, estimate cell count and runtime:
```bash
curl -X POST http://localhost:8000/api/v1/jobs/estimate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "cafe",
    "area_name": "Indiranagar, Bangalore",
    "cell_size_m": 500
  }'
```

### 2. Launch Scrape & Analysis Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "cafe",
    "area_name": "Indiranagar, Bangalore",
    "cell_size_m": 500,
    "consent_google_tos": true
  }'
```

### 3. Retrieve Gap Intelligence & GeoJSON
Once `status == "completed"`, retrieve the hexagonal GeoJSON metrics:
```bash
curl http://localhost:8000/api/v1/gap/<JOB_ID> \
  -H "Authorization: Bearer <TOKEN>"
```

### Interpretation:
- **Opportunity Score $\ge 70$ ("underserved"):** High footfall anchor density with low competitor presence. Prime locations for expansion or agency outreach.
- **Opportunity Score 45–69 ("balanced"):** Moderate competition aligned with footfall demand.
- **Opportunity Score $< 45$ ("oversaturated"):** Dense cluster of competing businesses with low individual market share.
