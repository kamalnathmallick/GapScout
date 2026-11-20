# ADR 0005: Grounded Draft-Only Outreach and Zero Auto-Send

## Status
Accepted

## Context
Automated outbound messaging tools often cause severe negative brand reputation, spam blacklisting, and compliance violations (CAN-SPAM, GDPR, WhatsApp Business Policies). Furthermore, unconstrained LLMs are prone to hallucinating non-existent metrics, discount promises, or fake customer complaints.

## Decision
We enforce a strict **Draft-Only, Grounded Human-in-the-Loop Architecture**:
1. **Zero Auto-Send Paths:** The application has no API integration, background worker, or mechanism to dispatch emails, SMS, or WhatsApp messages autonomously. It generates drafts; a human must review, approve, and send.
2. **Deterministic Fallback Templates:** When LLM enrichment is unavailable or disabled, high-converting rule templates assemble personalized copy directly from place attributes.
3. **Strict Length & Channel Caps:**
   - WhatsApp / Chat: $\le 450$ characters total.
   - Cold Email: $\le 120$ words total.
4. **Mandatory Opt-Out Line:** Every draft template includes a standard opt-out mechanism (e.g., *"If you'd prefer I don't reach out again, reply 'stop' and I will remove your details."*).
5. **Factual Grounding & Hallucination Prevention:** The LLM is given explicit instructions to cite only extracted review themes or website audit issues (`[citations]`). Inventing metrics or statistics is strictly forbidden; if a metric is unavailable, the prompt requires bracketed placeholders (`[N]`).
6. **Do-Not-Contact (DNC) Lock:** Any email, phone number, or root domain on the workspace DNC list blocks draft generation and UI outreach actions.

## Consequences & Trade-offs
### Advantages:
- 100% human oversight prevents spam and brand reputation damage.
- Zero risk of runaway automated email campaigns or carrier blacklists.
- Full compliance with international anti-spam legislation.
