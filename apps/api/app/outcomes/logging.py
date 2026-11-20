"""Outcome logging and CSV import service."""

import csv
import io
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead, LeadFeature, OutreachEvent, Place

logger = logging.getLogger(__name__)

VALID_OUTCOMES = {"replied", "no_reply", "meeting", "converted"}


class OutcomeError(ValueError):
    """Raised on invalid outcome logging requests."""

    pass


def log_lead_outcome(
    session: Session,
    lead_id: uuid.UUID,
    outcome: str,
    occurred_at: datetime | None = None,
    notes: str | None = None,
) -> OutreachEvent:
    """Log an outcome event (replied, no_reply, meeting, converted) for a contacted lead."""
    clean_outcome = outcome.strip().lower()
    if clean_outcome not in VALID_OUTCOMES:
        raise OutcomeError(f"Invalid outcome '{outcome}'. Must be one of {sorted(VALID_OUTCOMES)}")

    lead = session.get(Lead, lead_id)
    if not lead:
        raise OutcomeError(f"Lead {lead_id} not found")

    # If lead was not yet contacted, ensure a contacted event with frozen snapshot exists
    contacted_event = session.execute(
        select(OutreachEvent).where(
            OutreachEvent.lead_id == lead.id,
            OutreachEvent.event_type == "contacted",
        )
    ).scalar_one_or_none()

    now_utc = occurred_at or datetime.now(UTC)

    if not contacted_event:
        # Snapshot features retroactively at this moment
        feat_row = (
            session.execute(
                select(LeadFeature)
                .where(LeadFeature.lead_id == lead.id)
                .order_by(LeadFeature.computed_at.desc())
            )
            .scalars()
            .first()
        )
        snapshot = feat_row.features if feat_row else {}
        init_contact = OutreachEvent(
            workspace_id=lead.workspace_id,
            lead_id=lead.id,
            event_type="contacted",
            occurred_at=now_utc,
            features_snapshot=snapshot,
        )
        session.add(init_contact)

    # Record the outcome event
    event = OutreachEvent(
        workspace_id=lead.workspace_id,
        lead_id=lead.id,
        event_type=clean_outcome,
        occurred_at=now_utc,
        features_snapshot=None,
    )
    session.add(event)

    # Update lead status when applicable
    if clean_outcome in {"replied", "meeting", "converted"}:
        lead.status = clean_outcome
    if notes:
        lead.notes = (
            f"{lead.notes}\n[Outcome {clean_outcome}]: {notes}".strip() if lead.notes else notes
        )

    session.commit()
    session.refresh(event)
    return event


def import_outcomes_from_csv(
    session: Session,
    workspace_id: uuid.UUID,
    csv_text: str,
) -> dict[str, Any]:
    """Import externally tracked outcomes from CSV format.

    Supported headers (case-insensitive):
    - lead_id OR email OR domain OR place_name
    - outcome (replied, no_reply, meeting, converted)
    - date / occurred_at (optional ISO format)
    """
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise OutcomeError("CSV is empty or missing headers.")

    field_map = {fn.strip().lower(): fn for fn in reader.fieldnames}
    outcome_col = field_map.get("outcome") or field_map.get("status")
    if not outcome_col:
        raise OutcomeError("CSV must include an 'outcome' or 'status' column.")

    imported = 0
    skipped = 0
    errors: list[str] = []

    for row_idx, row in enumerate(reader, start=1):
        outcome_val = (row.get(outcome_col) or "").strip().lower()
        if outcome_val not in VALID_OUTCOMES:
            errors.append(f"Row {row_idx}: Invalid outcome '{outcome_val}'")
            skipped += 1
            continue

        target_lead: Lead | None = None

        # 1. Match by lead_id
        lead_id_key = field_map.get("lead_id")
        if lead_id_key and row.get(lead_id_key):
            try:
                lid = uuid.UUID(row[lead_id_key].strip())
                target_lead = session.get(Lead, lid)
            except ValueError:
                pass

        # 2. Match by email
        email_key = field_map.get("email")
        if not target_lead and email_key and row.get(email_key):
            clean_email = row[email_key].strip().lower()
            stmt = (
                select(Lead)
                .join(Place, Place.id == Lead.place_id)
                .where(
                    Lead.workspace_id == workspace_id,
                    Place.email == clean_email,
                )
            )
            target_lead = session.execute(stmt).scalars().first()

        # 3. Match by domain
        domain_key = field_map.get("domain") or field_map.get("website_domain")
        if not target_lead and domain_key and row.get(domain_key):
            clean_domain = row[domain_key].strip().lower()
            stmt = (
                select(Lead)
                .join(Place, Place.id == Lead.place_id)
                .where(
                    Lead.workspace_id == workspace_id,
                    Place.website_domain == clean_domain,
                )
            )
            target_lead = session.execute(stmt).scalars().first()

        # 4. Match by business/place name
        name_key = field_map.get("place_name") or field_map.get("name") or field_map.get("business")
        if not target_lead and name_key and row.get(name_key):
            biz_name = row[name_key].strip()
            stmt = (
                select(Lead)
                .join(Place, Place.id == Lead.place_id)
                .where(
                    Lead.workspace_id == workspace_id,
                    Place.name.ilike(biz_name),
                )
            )
            target_lead = session.execute(stmt).scalars().first()

        if not target_lead or target_lead.workspace_id != workspace_id:
            errors.append(f"Row {row_idx}: No matching lead found in workspace.")
            skipped += 1
            continue

        # Optional date
        date_key = field_map.get("occurred_at") or field_map.get("date")
        occurred_dt = None
        if date_key and row.get(date_key):
            try:
                occurred_dt = datetime.fromisoformat(row[date_key].strip())
            except ValueError:
                occurred_dt = None

        log_lead_outcome(
            session=session,
            lead_id=target_lead.id,
            outcome=outcome_val,
            occurred_at=occurred_dt,
        )
        imported += 1

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:20],  # Return up to first 20 errors
    }
