"""Leak-free training dataset builder and health monitor from real outreach outcomes."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead, OutreachEvent, Place
from app.services.dnc import is_lead_dnc

logger = logging.getLogger(__name__)

ML_MIN_LABELS = 150
ML_MIN_POSITIVES = 20
DEFAULT_WINDOW_DAYS = 14


def build_training_dataset(
    session: Session,
    workspace_id: uuid.UUID | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[dict[str, Any]]:
    """Build a leak-free dataset using frozen features_snapshot from contacted events only.

    Rules:
    1. Positive label (1): Replied within window_days of contact time.
    2. Negative label (0): No reply after window_days, or explicitly logged no_reply.
    3. Ambiguous / open window: Contacted < window_days ago with no outcome yet -> EXCLUDED.
    4. DNC / Opt-out leads: Strictly EXCLUDED.
    5. Zero leakage: Every feature MUST come from the contacted event snapshot, never current state.
    """
    stmt = (
        select(Lead, Place)
        .join(Place, Place.id == Lead.place_id)
        .where(Lead.status != "do_not_contact")
    )
    if workspace_id:
        stmt = stmt.where(Lead.workspace_id == workspace_id)

    leads_and_places = session.execute(stmt).all()
    now_utc = datetime.now(UTC)
    dataset: list[dict[str, Any]] = []

    for lead, place in leads_and_places:
        # Exclude DNC leads
        if is_lead_dnc(session, lead, place):
            continue

        # Get all events for lead sorted by time
        events_stmt = (
            select(OutreachEvent)
            .where(OutreachEvent.lead_id == lead.id)
            .order_by(OutreachEvent.occurred_at.asc())
        )
        events = list(session.execute(events_stmt).scalars().all())
        if not events:
            continue

        # Find initial contacted event
        contact_event = next((e for e in events if e.event_type == "contacted"), None)
        if not contact_event or not contact_event.features_snapshot:
            # Cannot train without a verified frozen snapshot at contact time
            continue

        contacted_at = contact_event.occurred_at
        if contacted_at.tzinfo is None:
            contacted_at = contacted_at.replace(tzinfo=UTC)

        window_end = contacted_at + timedelta(days=window_days)

        # Look for reply events within the window
        positive_event = next(
            (
                e
                for e in events
                if e.event_type in {"replied", "meeting", "converted"}
                and e.occurred_at <= window_end
            ),
            None,
        )

        explicit_negative = next((e for e in events if e.event_type == "no_reply"), None)

        if positive_event:
            label = 1
            secondary_label = positive_event.event_type
        elif explicit_negative or now_utc > window_end:
            label = 0
            secondary_label = "no_reply"
        else:
            # Window is still open (< 14 days and no reply yet) -> Ambiguous, omit from dataset
            continue

        dataset.append(
            {
                "lead_id": str(lead.id),
                "workspace_id": str(lead.workspace_id),
                "contacted_at": contacted_at.isoformat(),
                "label": label,
                "secondary_label": secondary_label,
                "features": dict(contact_event.features_snapshot),
            }
        )

    return dataset


def get_dataset_health(
    session: Session,
    workspace_id: uuid.UUID | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Calculate dataset volume, positive rate, and cold-start unlocking status."""
    dataset = build_training_dataset(
        session=session,
        workspace_id=workspace_id,
        window_days=window_days,
    )
    total_labelled = len(dataset)
    positives = sum(1 for row in dataset if row["label"] == 1)
    negatives = total_labelled - positives
    positive_rate = round(positives / total_labelled, 4) if total_labelled > 0 else 0.0

    unlocked = (total_labelled >= ML_MIN_LABELS) and (positives >= ML_MIN_POSITIVES)
    labels_needed = max(0, ML_MIN_LABELS - total_labelled)
    positives_needed = max(0, ML_MIN_POSITIVES - positives)

    return {
        "total_labelled": total_labelled,
        "positives_count": positives,
        "negatives_count": negatives,
        "positive_rate": positive_rate,
        "min_labels_required": ML_MIN_LABELS,
        "min_positives_required": ML_MIN_POSITIVES,
        "unlocked": unlocked,
        "labels_needed": labels_needed,
        "positives_needed": positives_needed,
    }
