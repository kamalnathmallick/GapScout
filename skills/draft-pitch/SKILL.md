---
name: draft-pitch
description: Generate grounded outreach drafts (email / WhatsApp) with review citations and mandatory opt-outs.
---

# Draft Pitch Skill

Use this skill to generate compliant, personalized outreach drafts for scored prospects.

## Constraints & Guardrails
- **Zero Auto-Send:** Generated copy is never sent autonomously. It is stored as a draft for human review.
- **Channel Length Caps:**
  - `email`: $\le 120$ words.
  - `chat` (WhatsApp): $\le 450$ characters.
- **Mandatory Opt-Out:** Every draft includes an explicit opt-out line (e.g., *"If you'd prefer I don't reach out, reply 'stop'"*).
- **Grounded Citations:** LLM only cites actual review themes or website findings. If specific figures are missing, placeholders (`[N]`) are used.

## API Usage

### Generate Outreach Draft
```bash
curl -X POST http://localhost:8000/api/v1/leads/<LEAD_ID>/draft \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "email"
  }'
```

Returns:
- `body`: Grounded outreach text.
- `word_count`: Number of words.
- `char_count`: Character count.
- `mailto_link`: One-click native email client launcher.
- `wa_link`: One-click WhatsApp web launcher (for chat channel).
