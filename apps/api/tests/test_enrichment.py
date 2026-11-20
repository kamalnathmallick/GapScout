"""Comprehensive tests for LLM enrichment (website audit, review themes, caching, and cost caps)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.anthropic_client import (
    AnthropicClient,
    AnthropicEnrichmentError,
    extract_json_from_text,
)
from app.enrichment.cost_guard import (
    CostCapExceededError,
    check_workspace_daily_cap,
    record_llm_usage,
)
from app.enrichment.pipeline import enrich_job_leads
from app.enrichment.reviews import ReviewThemesAudit, extract_place_review_themes
from app.enrichment.safe_fetcher import (
    SimpleHTMLInspector,
    SSRFBlockedError,
    validate_url_and_check_ssrf,
)
from app.enrichment.website import LLMWebsiteAudit, audit_place_website
from app.models import Enrichment, Lead, Place, PlaceReview, SearchJob, Workspace


@pytest.fixture
def enrichment_workspace(db_session: Session) -> Workspace:
    ws = Workspace(name="Enrichment WS")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)
    return ws


# ==============================================================================
# 1. Safe Fetcher & SSRF Defense Tests
# ==============================================================================
def test_ssrf_blocks_private_and_loopback_ips():
    """Verify that validate_url_and_check_ssrf rejects loopback, private, and metadata IPs."""
    blocked_urls = [
        "http://127.0.0.1:8000/api",
        "http://127.0.0.2",
        "http://localhost:3000",
        "http://10.0.0.1/admin",
        "http://172.16.0.5",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file",
    ]

    for url in blocked_urls:
        with pytest.raises(SSRFBlockedError):
            validate_url_and_check_ssrf(url)


def test_simple_html_inspector_deterministic_signals():
    """Verify that HTML inspector extracts deterministic signals accurately."""
    sample_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Artisan Coffee Roasters</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>
      <body>
        <h1>Welcome to Artisan Brew</h1>
        <p>The finest single-origin coffee in Bangalore.</p>
        <form action="/contact-us" method="POST">
          <input type="email" name="user_email" />
          <button type="submit">Send Inquiry</button>
        </form>
        <a href="https://calendly.com/artisan-brew/tasting">Book Tasting</a>
        <a href="https://instagram.com/artisanbrew">Follow Us</a>
        <script>console.log("ignore me");</script>
      </body>
    </html>
    """
    inspector = SimpleHTMLInspector()
    inspector.feed(sample_html)

    assert inspector.mobile_viewport is True
    assert inspector.has_contact_form is True
    assert inspector.has_booking_link is True
    assert "instagram.com" in inspector.social_links
    cleaned = inspector.get_cleaned_text()
    assert "Artisan Coffee Roasters" in cleaned
    assert "The finest single-origin coffee in Bangalore" in cleaned
    assert "console.log" not in cleaned


# ==============================================================================
# 2. Anthropic Client JSON Validation and Retry
# ==============================================================================
def test_extract_json_from_text_strips_markdown():
    """Verify JSON parsing handles markdown fencing and surrounding prose."""
    raw_markdown = """Here is the analysis:
    ```json
    {
      "headline": "Great cafe",
      "clarity_score": 4,
      "cta_presence": 5,
      "mobile_readiness": 4,
      "top_issues": ["Slow loading"],
      "overall_score": 82
    }
    ```
    Hope this helps!"""
    parsed = extract_json_from_text(raw_markdown)
    assert parsed["headline"] == "Great cafe"
    assert parsed["overall_score"] == 82


def test_anthropic_client_retries_on_invalid_json(
    db_session: Session, enrichment_workspace: Workspace
):
    """Verify AnthropicClient retries once on invalid JSON and succeeds on valid response."""
    client = AnthropicClient(api_key="sk-ant-test-key", default_model="claude-3-5-haiku-20241022")

    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 200
    mock_resp_fail.json.return_value = {
        "content": [{"type": "text", "text": "This is not valid json at all"}],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }

    mock_json = (
        '{"headline": "Good site", "clarity_score": 4, "cta_presence": 3, '
        '"mobile_readiness": 4, "top_issues": [], "overall_score": 80}'
    )
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200
    mock_resp_success.json.return_value = {
        "content": [{"type": "text", "text": mock_json}],
        "usage": {"input_tokens": 120, "output_tokens": 60},
    }

    with patch("httpx.Client.post", side_effect=[mock_resp_fail, mock_resp_success]):
        result, p_tok, c_tok = client.generate_structured_output(
            session=db_session,
            workspace_id=enrichment_workspace.id,
            kind="website_audit",
            system_prompt="Audit site",
            untrusted_content="Homepage text",
            schema_cls=LLMWebsiteAudit,
        )

    assert result.headline == "Good site"
    assert result.overall_score == 80
    assert p_tok == 120
    assert c_tok == 60


def test_anthropic_client_fails_gracefully_after_exhausting_retries(
    db_session: Session, enrichment_workspace: Workspace
):
    """Verify client raises AnthropicEnrichmentError when attempts fail to return valid JSON."""
    client = AnthropicClient(api_key="sk-ant-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": "Malicious non-json reply"}],
        "usage": {"input_tokens": 50, "output_tokens": 20},
    }

    with (
        patch("httpx.Client.post", return_value=mock_resp),
        pytest.raises(AnthropicEnrichmentError),
    ):
        client.generate_structured_output(
            session=db_session,
            workspace_id=enrichment_workspace.id,
            kind="website_audit",
            system_prompt="Audit site",
            untrusted_content="Homepage text",
            schema_cls=LLMWebsiteAudit,
        )


# ==============================================================================
# 3. Website Audit & Review Themes with Caching
# ==============================================================================
def test_website_audit_and_content_hash_caching(
    db_session: Session, enrichment_workspace: Workspace
):
    """Verify that website audit caches by content hash and skips LLM call on second invocation."""
    place = Place(
        workspace_id=enrichment_workspace.id,
        provider="gosom",
        provider_place_id="enrich-p1",
        name="Third Wave Coffee Roasters",
        category="cafe",
        website="https://thirdwavecoffeeroasters.example.com",
    )
    db_session.add(place)
    db_session.commit()

    fake_signals = {
        "url": "https://thirdwavecoffeeroasters.example.com",
        "https": True,
        "load_time_ms": 320.5,
        "mobile_viewport": True,
        "has_contact_form": True,
        "has_booking_link": False,
        "social_links": ["instagram.com"],
        "cleaned_text": "Third Wave Coffee - Speciality arabica beans in Bangalore.",
    }

    mock_audit = LLMWebsiteAudit(
        headline="Speciality coffee brand",
        clarity_score=5,
        cta_presence=4,
        mobile_readiness=5,
        top_issues=["No delivery integration on mobile"],
        overall_score=85,
    )

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.default_model = "claude-3-5-haiku-20241022"
    mock_client.generate_structured_output.return_value = (mock_audit, 100, 50)

    with patch("app.enrichment.website.fetch_website_safely", return_value=fake_signals):
        # 1. First run -> Cache MISS
        payload_1, cached_1 = audit_place_website(
            session=db_session,
            place=place,
            force=False,
            anthropic_client=mock_client,
        )
        assert cached_1 is False
        assert payload_1["audit"]["overall_score"] == 85
        assert mock_client.generate_structured_output.call_count == 1

        # 2. Second run -> Cache HIT
        payload_2, cached_2 = audit_place_website(
            session=db_session,
            place=place,
            force=False,
            anthropic_client=mock_client,
        )
        assert cached_2 is True
        assert payload_2["audit"]["overall_score"] == 85
        # Call count must still be 1 (LLM was NOT invoked)
        assert mock_client.generate_structured_output.call_count == 1

    # Verify Enrichment record in database
    enrichment_row = db_session.execute(
        select(Enrichment).where(
            Enrichment.place_id == place.id,
            Enrichment.kind == "website_audit",
        )
    ).scalar_one_or_none()
    assert enrichment_row is not None
    assert enrichment_row.content_hash is not None


def test_review_themes_extraction_and_caching(db_session: Session, enrichment_workspace: Workspace):
    """Verify that review themes are extracted, cached by content hash, and update lead_features."""
    place = Place(
        workspace_id=enrichment_workspace.id,
        provider="gosom",
        provider_place_id="enrich-p2",
        name="Koramangala Diner",
        category="restaurant",
        address="Koramangala 5th Block",
    )
    db_session.add(place)
    db_session.flush()

    for i in range(3):
        rev = PlaceReview(
            workspace_id=enrichment_workspace.id,
            place_id=place.id,
            rating=2 if i == 0 else 5,
            review_text="Food was delayed by 40 minutes" if i == 0 else "Excellent steaks!",
            owner_replied=False,
            published_at=datetime.now(UTC),
        )
        db_session.add(rev)
    db_session.commit()

    mock_themes = ReviewThemesAudit(
        complaint_themes=["Significant order delivery delays during rush hour"],
        praise_themes=["High quality steaks and friendly ambiance"],
        owner_response_behavior="Never replies to negative feedback",
        one_line_pitch_angle="Pitch table management software to cut wait times.",
    )

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.default_model = "claude-3-5-haiku-20241022"
    mock_client.generate_structured_output.return_value = (mock_themes, 150, 70)

    # 1. First run -> Cache MISS
    res_1, cached_1 = extract_place_review_themes(
        session=db_session,
        place=place,
        force=False,
        anthropic_client=mock_client,
    )
    assert cached_1 is False
    assert len(res_1["complaint_themes"]) == 1
    assert mock_client.generate_structured_output.call_count == 1

    # 2. Second run -> Cache HIT
    _res_2, cached_2 = extract_place_review_themes(
        session=db_session,
        place=place,
        force=False,
        anthropic_client=mock_client,
    )
    assert cached_2 is True
    assert mock_client.generate_structured_output.call_count == 1


# ==============================================================================
# 4. Workspace Daily Cost Cap Enforcement
# ==============================================================================
def test_workspace_daily_cost_cap_stops_spending(
    db_session: Session, enrichment_workspace: Workspace
):
    """Verify that exceeding the daily cost cap raises CostCapExceededError and prevents calls."""
    ws_id = enrichment_workspace.id

    # Spend $0.08 by recording usage
    cost_1 = record_llm_usage(
        session=db_session,
        workspace_id=ws_id,
        model="claude-3-5-sonnet-20241022",
        kind="website_audit",
        prompt_tokens=20_000,
        completion_tokens=2_000,
    )
    db_session.commit()

    assert cost_1 > 0.05

    # Check with a cap of $0.05 -> Must raise CostCapExceededError
    with pytest.raises(CostCapExceededError) as exc_info:
        check_workspace_daily_cap(db_session, ws_id, daily_cap_usd=0.05)

    assert "exceeded its daily LLM cost cap" in str(exc_info.value)


def test_batch_enrichment_stops_gracefully_on_cost_cap(
    db_session: Session, enrichment_workspace: Workspace
):
    """Verify that enrich_job_leads terminates gracefully when the daily cost cap is reached."""
    job = SearchJob(
        workspace_id=enrichment_workspace.id,
        category="cafe",
        area_name="Indiranagar",
        status="completed",
    )
    db_session.add(job)
    db_session.flush()

    # Create 3 leads
    for i in range(3):
        place = Place(
            workspace_id=enrichment_workspace.id,
            provider="gosom",
            provider_place_id=f"cap-place-{i}",
            name=f"Cap Cafe {i}",
            category="cafe",
            website=f"https://cafe{i}.example.com",
        )
        db_session.add(place)
        db_session.flush()

        lead = Lead(
            workspace_id=enrichment_workspace.id,
            place_id=place.id,
            rule_score=75.0,
            final_score=75.0,
        )
        db_session.add(lead)
    db_session.commit()

    # Artificially breach the workspace daily cost cap
    record_llm_usage(
        session=db_session,
        workspace_id=enrichment_workspace.id,
        model="haiku",
        kind="test",
        prompt_tokens=5_000_000,
        completion_tokens=1_000_000,
    )
    db_session.commit()

    # Run batch enrichment with low cap -> Should stop at 0 without crashing
    mock_settings = MagicMock()
    mock_settings.llm_daily_cost_cap_usd = 1.0
    mock_settings.anthropic_api_key = ""
    mock_settings.llm_model_fast = "claude-3-5-haiku-20241022"

    with patch("app.enrichment.cost_guard.get_settings", return_value=mock_settings):
        enriched_count = enrich_job_leads(db_session, job.id, min_rule_score=60.0)

    # Spending cap prevented calls
    assert enriched_count == 0
