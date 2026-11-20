"""Tests for Prompt 13: Outcome logging, snapshot immutability, and dataset builder."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import (
    Lead,
    LeadFeature,
    OutreachEvent,
    Place,
    Workspace,
)
from app.outcomes.dataset import (
    ML_MIN_LABELS,
    ML_MIN_POSITIVES,
    build_training_dataset,
    get_dataset_health,
)
from app.outcomes.logging import import_outcomes_from_csv, log_lead_outcome
from app.tasks import close_outreach_windows_task


@pytest.fixture
def workspace_with_leads(db_session):
    """Seed workspace and 3 leads for testing outcomes."""
    ws = Workspace(name="Outcome Test Workspace")
    db_session.add(ws)
    db_session.flush()

    leads = []
    places = []

    for idx, name in enumerate(["Alpha Clinic", "Beta Spa", "Gamma Salon"]):
        place = Place(
            workspace_id=ws.id,
            provider="test",
            provider_place_id=f"p_{uuid.uuid4().hex[:8]}",
            name=name,
            category="Health",
            normalized_category="health",
            phone_e164=f"+91987654321{idx}",
            email=f"{name.lower().replace(' ', '')}@example.com",
            website_domain=f"{name.lower().replace(' ', '')}.com",
            rating=4.2,
            review_count=50,
        )
        db_session.add(place)
        db_session.flush()

        lead = Lead(
            workspace_id=ws.id,
            place_id=place.id,
            status="new",
            rule_score=80.0,
            final_score=80.0,
            score_breakdown={"pain": {"points": 20, "max": 30}},
        )
        db_session.add(lead)
        db_session.flush()

        feat = LeadFeature(
            workspace_id=ws.id,
            lead_id=lead.id,
            feature_version="v1",
            features={
                "rating": 4.2,
                "review_count": 50,
                "has_email": 1,
                "business_name": name,
            },
        )
        db_session.add(feat)
        leads.append(lead)
        places.append(place)

    db_session.commit()
    return ws, places, leads


def test_snapshot_immutability_and_leakage_prevention(db_session, workspace_with_leads):
    """LEAKAGE TEST: Changes to Place or LeadFeature after contact do not alter dataset."""
    ws, places, leads = workspace_with_leads
    lead = leads[0]
    place = places[0]

    # Contact lead at T0
    contact_time = datetime.now(UTC) - timedelta(days=20)
    frozen_features = {
        "rating": 4.2,
        "review_count": 50,
        "historic_marker": "frozen_at_contact",
    }
    contact_ev = OutreachEvent(
        workspace_id=ws.id,
        lead_id=lead.id,
        event_type="contacted",
        occurred_at=contact_time,
        features_snapshot=frozen_features,
    )
    db_session.add(contact_ev)
    lead.status = "contacted"
    db_session.commit()

    # Log positive outcome at T1 (5 days after contact)
    log_lead_outcome(
        session=db_session,
        lead_id=lead.id,
        outcome="replied",
        occurred_at=contact_time + timedelta(days=5),
    )

    # SUBSEQUENT POST-CONTACT MUTATIONS AT T2 (Simulating real-world updates)
    place.rating = 1.0  # Dropped from 4.2 to 1.0
    place.review_count = 500  # Increased from 50 to 500
    db_session.commit()

    # Re-compute new lead features post-contact
    new_feat = LeadFeature(
        workspace_id=ws.id,
        lead_id=lead.id,
        feature_version="v2",
        features={
            "rating": 1.0,
            "review_count": 500,
            "historic_marker": "future_leak_danger",
        },
    )
    db_session.add(new_feat)
    db_session.commit()

    # Build dataset
    dataset = build_training_dataset(session=db_session, workspace_id=ws.id)
    assert len(dataset) == 1
    row = dataset[0]

    # Assert label and snapshot
    assert row["lead_id"] == str(lead.id)
    assert row["label"] == 1
    assert row["secondary_label"] == "replied"

    # CRITICAL LEAKAGE ASSERTIONS
    assert row["features"]["rating"] == 4.2  # Frozen value preserved
    assert row["features"]["review_count"] == 50  # Frozen value preserved
    assert row["features"]["historic_marker"] == "frozen_at_contact"
    assert "future_leak_danger" not in str(row["features"])


def test_window_closing_celery_task(db_session, workspace_with_leads):
    """Verify 14-day window closing logic: overdue contacted leads get no_reply."""
    ws, _places, leads = workspace_with_leads
    lead_old = leads[0]
    lead_recent = leads[1]

    now_utc = datetime.now(UTC)

    # Lead 1: Contacted 16 days ago (> 14 days)
    ev_old = OutreachEvent(
        workspace_id=ws.id,
        lead_id=lead_old.id,
        event_type="contacted",
        occurred_at=now_utc - timedelta(days=16),
        features_snapshot={"metric": 10},
    )
    db_session.add(ev_old)

    # Lead 2: Contacted 3 days ago (< 14 days)
    ev_recent = OutreachEvent(
        workspace_id=ws.id,
        lead_id=lead_recent.id,
        event_type="contacted",
        occurred_at=now_utc - timedelta(days=3),
        features_snapshot={"metric": 20},
    )
    db_session.add(ev_recent)
    db_session.commit()

    # Run celery beat window-closing task
    closed = close_outreach_windows_task(days_window=14, db_session=db_session)
    assert closed == 1

    # Lead 1 must now have a no_reply event
    no_reply_ev = (
        db_session.query(OutreachEvent)
        .filter_by(lead_id=lead_old.id, event_type="no_reply")
        .first()
    )
    assert no_reply_ev is not None

    # Lead 2 must NOT have a no_reply event (window is still active)
    recent_no_reply = (
        db_session.query(OutreachEvent)
        .filter_by(lead_id=lead_recent.id, event_type="no_reply")
        .first()
    )
    assert recent_no_reply is None

    # Dataset builder should include lead_old (label=0) and exclude lead_recent (pending)
    ds = build_training_dataset(session=db_session, workspace_id=ws.id)
    assert len(ds) == 1
    assert ds[0]["lead_id"] == str(lead_old.id)
    assert ds[0]["label"] == 0


def test_csv_outcome_import(db_session, workspace_with_leads):
    """Verify importing outcomes via CSV matching by email or business name."""
    ws, _places, leads = workspace_with_leads

    csv_data = (
        "email,outcome,date\n"
        "alphaclinic@example.com,meeting,2026-11-15T10:00:00\n"
        "betaspa@example.com,converted,2026-11-16T12:00:00\n"
    )

    result = import_outcomes_from_csv(
        session=db_session,
        workspace_id=ws.id,
        csv_text=csv_data,
    )
    assert result["imported"] == 2
    assert result["skipped"] == 0

    lead_alpha = db_session.get(Lead, leads[0].id)
    assert lead_alpha.status == "meeting"

    lead_beta = db_session.get(Lead, leads[1].id)
    assert lead_beta.status == "converted"


def test_dataset_health_and_ml_gating(db_session, workspace_with_leads):
    """Verify dataset health summary metrics and cold-start unlocking gate."""
    ws, _, _ = workspace_with_leads

    health = get_dataset_health(session=db_session, workspace_id=ws.id)
    assert health["total_labelled"] == 0
    assert health["unlocked"] is False
    assert health["labels_needed"] == ML_MIN_LABELS
    assert health["positives_needed"] == ML_MIN_POSITIVES
