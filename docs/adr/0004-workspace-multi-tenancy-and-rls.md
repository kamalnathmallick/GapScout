# ADR 0004: Workspace Multi-Tenancy and Isolation Hardening

## Status
Accepted

## Context
GapScout serves multiple agencies, freelancers, and businesses in shared infrastructure. Outreach drafts, prospect notes, offer profiles, and logged client interactions contain proprietary and sensitive commercial intelligence. Strict multi-tenancy is required to prevent data leakage between workspaces.

## Decision
We enforce multi-tenancy through **Strict Tenant Scoping at the Database Layer**:
1. **Explicit Foreign Key (`workspace_id`):** Every tenant entity (`places`, `search_jobs`, `leads`, `outreach_events`, `outreach_drafts`, `model_versions`, `do_not_contact`, `offer_profiles`) includes a non-nullable foreign key referencing `workspaces.id` with `ondelete="CASCADE"`.
2. **Context-Injected Queries:** All service and API repository queries inject `workspace_id == current_user.workspace_id` into the SQL `WHERE` clause.
3. **Automated Tenant Boundary Testing:** Test suite contains explicit adversarial cross-tenant access assertions proving that User A cannot read, update, or delete User B's jobs, leads, models, or settings (returning HTTP 404 or 403).
4. **Irreversible Data Erasure:** Full GDPR/CCPA compliance via an atomic `delete-my-data` endpoint that cascades deletions across all workspace data.

## Consequences & Trade-offs
### Advantages:
- Eliminates accidental cross-tenant data leakage.
- Simplifies account export (JSON/CSV) and deletion.
- Supports future migration to PostgreSQL Row-Level Security (RLS) policies if needed.
