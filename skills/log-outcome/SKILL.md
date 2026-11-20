---
name: log-outcome
description: Log contact events, capture frozen feature snapshots, record replies, and trigger ML retraining.
---

# Log Outcome Skill

Use this skill to record real-world outreach outcomes and train the self-improving ML pipeline.

## Outreach Lifecycle

### 1. Mark Contacted
Freezes the lead's current feature vector into an immutable `features_snapshot` to guarantee zero future data leakage:
```bash
curl -X POST http://localhost:8000/api/v1/leads/<LEAD_ID>/contact \
  -H "Authorization: Bearer <TOKEN>"
```

### 2. Log Reply (Positive Outcome)
Records a positive reply label within the 14-day window:
```bash
curl -X POST http://localhost:8000/api/v1/leads/<LEAD_ID>/reply \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Owner replied interested in weekday afternoon promotion."
  }'
```

### 3. Check Dataset Health & Retraining Progress
```bash
curl http://localhost:8000/api/v1/models/dataset/health \
  -H "Authorization: Bearer <TOKEN>"
```
Returns:
- `total_labelled`: Total completed outcomes ($N \ge 150$ required for ML tournament).
- `positives_count`: Total positive outcomes ($P \ge 20$ required).
- `unlocked`: Whether machine learning models are active.
- `labels_needed`: Remaining labels needed to unlock/retrain.
