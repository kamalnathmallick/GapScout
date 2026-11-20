---
name: lead-rank
description: Query and rank leads by conversion potential using transparent rules and calibrated ML scores.
---

# Lead Rank Skill

Use this skill to fetch, filter, and inspect scored leads in the workspace.

## API Usage

### 1. Fetch Top Leads
```bash
curl "http://localhost:8000/api/v1/leads?order_by=final_score&order_dir=desc&limit=25" \
  -H "Authorization: Bearer <TOKEN>"
```

### 2. Inspect "Why This Score" for a Specific Lead
```bash
curl http://localhost:8000/api/v1/leads/<LEAD_ID> \
  -H "Authorization: Bearer <TOKEN>"
```
Returns:
- `rule_score`: 0–100 points across Pain, Fit, Timing, Reachability, and Evidence.
- `ml_score`: Calibrated reply probability (0.00–1.00) if active model is trained.
- `final_score`: Weighted blend of rule score and ML probability.
- `score_breakdown`: Point allocations and textual explanations for each rule component.

### 3. Fetch Active Learning Queue
Get leads prioritized for human feedback to improve the model fastest:
```bash
curl http://localhost:8000/api/v1/models/active-learning \
  -H "Authorization: Bearer <TOKEN>"
```
Queue prioritizes businesses in the maximum uncertainty zone ($0.35 \le p \le 0.65$) or high-scoring leads with thin evidence.
