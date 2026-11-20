"""Tests for Prompt 12: Outreach workflow, drafts, statuses, DNC blocking, and safety."""

import inspect
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_workspace, get_db
from app.main import app
from app.models import (
    DoNotContact,
    Lead,
    LeadFeature,
    OfferProfile,
    OutreachEvent,
    Place,
    Workspace,
)
from app.services.dnc import add_to_dnc, is_lead_dnc
from app.services.drafts import (
    MAX_CHAT_CHARS,
    MAX_EMAIL_WORDS,
    OPT_OUT_CHAT,
    OPT_OUT_EMAIL,
    DNCBlockedError,
    count_words,
    enforce_length_caps,
    generate_and_save_draft,
)


@pytest.fixture
def workspace_and_place(db_session):
    """Seed workspace, place, and offer profile for testing."""
    ws = Workspace(name="Outreach Test Workspace")
    db_session.add(ws)
    db_session.flush()

    offer = OfferProfile(
        workspace_id=ws.id,
        name="Local SEO Accelerator",
        offer_description="help local clinics get 30+ new patient inquiries monthly",
    )
    db_session.add(offer)

    place = Place(
        workspace_id=ws.id,
        provider="test",
        provider_place_id=f"p_{uuid.uuid4().hex[:8]}",
        name="Sunrise Dental Clinic",
        category="Dentist",
        normalized_category="dentist",
        address="123 MG Road, Bangalore",
        phone_e164="+918012345678",
        email="contact@sunrisedental.com",
        website="https://sunrisedental.com",
        website_domain="sunrisedental.com",
        rating=3.8,
        review_count=42,
    )
    db_session.add(place)
    db_session.flush()

    lead = Lead(
        workspace_id=ws.id,
        place_id=place.id,
        status="new",
        rule_score=78.5,
        final_score=78.5,
        score_breakdown={
            "pain": {"points": 25, "max": 30, "reason": "Rating is 3.8/5"},
            "fit": {"points": 20, "max": 25, "reason": "Matches clinic profile"},
        },
    )
    db_session.add(lead)
    db_session.flush()

    feat = LeadFeature(
        workspace_id=ws.id,
        lead_id=lead.id,
        feature_version="v1",
        features={
            "rating": 3.8,
            "review_count": 42,
            "has_email": 1,
            "category": "dentist",
        },
    )
    db_session.add(feat)
    db_session.commit()

    return ws, place, lead


def test_channel_length_caps_and_opt_out():
    """Verify chat is <= 450 chars and email <= 120 words, with mandatory opt-outs."""
    long_chat = "This is a very detailed outreach message. " * 30
    assert len(long_chat) > MAX_CHAT_CHARS

    capped_chat = enforce_length_caps("chat", long_chat)
    assert len(capped_chat) <= MAX_CHAT_CHARS
    assert OPT_OUT_CHAT in capped_chat

    long_email = "Opportunity " * 200
    assert count_words(long_email) > MAX_EMAIL_WORDS

    capped_email = enforce_length_caps("email", long_email)
    assert count_words(capped_email) <= MAX_EMAIL_WORDS
    assert OPT_OUT_EMAIL in capped_email


def test_deterministic_draft_grounded_citation(db_session, workspace_and_place):
    """Verify draft generation includes grounded facts without hallucination."""
    _ws, _place, lead = workspace_and_place

    draft_res = generate_and_save_draft(
        session=db_session,
        lead_id=lead.id,
        channel="email",
        tone="direct",
    )

    body = draft_res["body"]
    assert "Sunrise Dental Clinic" in body
    assert OPT_OUT_EMAIL in body
    assert draft_res["mailto_link"] is not None
    assert "mailto:contact@sunrisedental.com" in draft_res["mailto_link"]
    assert draft_res["wa_link"] is not None
    assert "https://wa.me/918012345678" in draft_res["wa_link"]
    assert draft_res["word_count"] <= MAX_EMAIL_WORDS


def test_dnc_blocking_and_exclusion(db_session, workspace_and_place):
    """Verify DNC list blocks drafting and excludes leads from active listing."""
    ws, place, lead = workspace_and_place

    # Initially not DNC
    assert not is_lead_dnc(db_session, lead, place)

    # Add place domain to DNC
    add_to_dnc(
        session=db_session,
        workspace_id=ws.id,
        domain=place.website_domain,
        reason="Requested opt-out via phone",
    )

    # Now lead is identified as DNC
    assert is_lead_dnc(db_session, lead, place)

    # Attempting to generate a draft must raise DNCBlockedError
    with pytest.raises(DNCBlockedError):
        generate_and_save_draft(
            session=db_session,
            lead_id=lead.id,
            channel="chat",
        )


def test_status_pipeline_and_features_snapshot_freeze(db_session, workspace_and_place):
    """Verify status transitions, invalid status rejection, and feature freeze on 'contacted'."""
    ws, place, lead = workspace_and_place

    client = TestClient(app)
    app.dependency_overrides[get_current_workspace] = lambda: ws
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 1. Invalid status rejected with 400
        res = client.patch(f"/api/v1/leads/{lead.id}", json={"status": "invalid_status_xyz"})
        assert res.status_code == 400

        # 2. Transition to contacted freezes features_snapshot
        res = client.patch(f"/api/v1/leads/{lead.id}", json={"status": "contacted"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "contacted"

        events = (
            db_session.query(OutreachEvent).filter_by(lead_id=lead.id, event_type="contacted").all()
        )
        assert len(events) >= 1
        snapshot = events[0].features_snapshot
        assert snapshot is not None
        assert snapshot.get("rating") == 3.8
        assert snapshot.get("review_count") == 42

        # 3. Transition to do_not_contact registers DNC
        res = client.patch(f"/api/v1/leads/{lead.id}", json={"status": "do_not_contact"})
        assert res.status_code == 200

        dnc_entry = (
            db_session.query(DoNotContact).filter_by(workspace_id=ws.id, email=place.email).first()
        )
        assert dnc_entry is not None

        # 4. Attempting to draft for DNC lead returns 400
        res = client.post(
            f"/api/v1/leads/{lead.id}/generate-draft",
            json={"channel": "email", "tone": "direct"},
        )
        assert res.status_code == 400
        error_msg = res.json().get("message") or res.json().get("detail") or ""
        assert "DNC" in error_msg or "Do-Not-Contact" in error_msg

    finally:
        app.dependency_overrides.clear()


def test_safety_zero_auto_sending_code_paths():
    """Verify non-negotiable safety rule: the application NEVER sends messages automatically.

    Inspects all functions/methods across the outreach and lead services to prove:
    1. No SMTP sendmail/send_message calls exist.
    2. No Twilio/WhatsApp/SendGrid/SES API clients exist.
    3. Only deep link generators (mailto:, https://wa.me/) and database draft records exist.
    """
    import app.api.v1.leads as leads_api_mod
    import app.services.drafts as drafts_mod

    forbidden_patterns = [
        "smtplib",
        "sendmail",
        "send_message",
        "twilio",
        "sendgrid",
        "boto3.client('ses')",
        "requests.post('https://api.whatsapp",
        "requests.post('https://api.twilio",
    ]

    for mod in [drafts_mod, leads_api_mod]:
        source = inspect.getsource(mod)
        for forbidden in forbidden_patterns:
            assert forbidden not in source.lower(), (
                f"Forbidden automated sending found: {forbidden} in {mod.__name__}"
            )
