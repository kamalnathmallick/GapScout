"""Tests for Lead Features and Rule-Based Scoring Engine (Prompt 10)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HexMetric, Lead, LeadFeature, OfferProfile, Place, PlaceReview, Workspace
from app.scoring.config import ScoringConfig, load_scoring_config
from app.scoring.features import FEATURE_VERSION, extract_lead_features
from app.scoring.pipeline import score_workspace_leads
from app.scoring.rules import (
    score_lead,
)


@pytest.fixture
def scoring_workspace(db_session: Session) -> Workspace:
    ws = Workspace(name="Scoring Test Workspace")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)
    return ws


def test_extract_lead_features(db_session: Session, scoring_workspace: Workspace):
    """Verify that extract_lead_features accurately computes all required deterministic features."""
    now = datetime.now(UTC)
    place = Place(
        workspace_id=scoring_workspace.id,
        provider="gosom",
        provider_place_id="feat-test-1",
        name="Indiranagar Roast Cafe",
        category="cafe",
        normalized_category="cafe",
        address="100 Feet Rd, Indiranagar, Bangalore",
        location=WKTElement("POINT(77.64 12.97)", srid=4326),
        phone_e164="+918025252525",
        website="https://indiroast.example.com",
        website_domain="indiroast.example.com",
        email="rahul.manager@indiroast.example.com",
        rating=3.6,
        review_count=120,
        price_level=2,
        h3_r8="88618925d3fffff",
        is_closed=False,
        raw={
            "is_named_email": True,
            "is_social_only": False,
            "hours": {"monday": "8am-10pm"},
        },
    )
    db_session.add(place)
    db_session.flush()

    # Add reviews
    r1 = PlaceReview(
        workspace_id=scoring_workspace.id,
        place_id=place.id,
        rating=2,
        review_text="Poor service and long wait time",
        owner_replied=False,
        published_at=now - timedelta(days=20),
    )
    r2 = PlaceReview(
        workspace_id=scoring_workspace.id,
        place_id=place.id,
        rating=5,
        review_text="Great coffee!",
        owner_replied=True,
        published_at=now - timedelta(days=5),
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    hex_metric = HexMetric(
        workspace_id=scoring_workspace.id,
        search_job_id=uuid.uuid4(),
        category="cafe",
        h3_index="88618925d3fffff",
        resolution=8,
        supply_count=2,
        opportunity_score=82.5,
        demand_proxy=65.0,
        label="underserved",
    )

    features = extract_lead_features(
        session=db_session,
        place=place,
        hex_metric=hex_metric,
        nearest_competitor_dist_m=450.0,
    )

    assert features["feature_version"] == FEATURE_VERSION
    assert features["category"] == "cafe"
    assert features["rating"] == 3.6
    assert features["review_count"] == 120
    assert features["log_review_count"] > 4.0
    assert features["has_real_website"] is True
    assert features["website_is_https"] is True
    assert features["has_phone"] is True
    assert features["has_named_email"] is True
    assert features["has_generic_email"] is False
    assert features["hours_complete"] is True
    assert features["owner_reply_rate"] == 0.5  # 1 out of 2
    assert features["negative_review_share"] == 0.5  # 1 rating <= 3 out of 2
    assert features["days_since_last_review"] == 5
    assert features["hex_opportunity_score"] == 82.5
    assert features["hex_supply_count"] == 2
    assert features["distance_to_nearest_competitor_m"] == 450.0


def test_hand_made_leads_obvious_ranking():
    """Verify high-pain, target-matching lead drastically outscores unfit, unreachable lead."""
    config = load_scoring_config()

    offer_profile = OfferProfile(
        name="Restaurant Marketing & Website Service",
        target_categories=["cafe", "restaurant"],
        min_rating=2.5,
        max_rating=4.2,
        target_regions=["Indiranagar"],
    )

    # Hand-made Lead A: "The Ideal Prospect"
    # - No website, low rating, recent unanswered negative reviews
    # - Matches cafe category in Indiranagar within rating range
    # - Direct named email and phone line
    # - High review volume with verified location
    lead_a_features = {
        "category": "cafe",
        "rating": 3.4,
        "review_count": 85,
        "has_real_website": False,
        "website_is_https": False,
        "has_phone": True,
        "has_named_email": True,
        "has_generic_email": False,
        "hours_complete": True,
        "owner_reply_rate": 0.0,
        "negative_review_share": 0.35,
        "days_since_last_review": 14,
        "hex_opportunity_score": 85.0,
    }
    place_a = Place(
        name="Indiranagar Daily Brew",
        address="12th Main, Indiranagar, Bangalore",
        location=WKTElement("POINT(77.64 12.97)", srid=4326),
    )

    score_a = score_lead(lead_a_features, place_a, offer_profile, config)

    # Hand-made Lead B: "The Unfit, Cold Prospect"
    # - Wrong category (dental clinic), pristine 4.9 rating, HTTPS website, no pain
    # - Outside target region, no email, no phone, old reviews
    lead_b_features = {
        "category": "dental clinic",
        "rating": 4.9,
        "review_count": 4,
        "has_real_website": True,
        "website_is_https": True,
        "has_phone": False,
        "has_named_email": False,
        "has_generic_email": False,
        "hours_complete": False,
        "owner_reply_rate": 0.0,
        "negative_review_share": 0.0,
        "days_since_last_review": 450,
        "hex_opportunity_score": 30.0,
    }
    place_b = Place(
        name="Whitefield Dental Care",
        address="ITPB Main Rd, Whitefield",
        location=None,
    )

    score_b = score_lead(lead_b_features, place_b, offer_profile, config)

    # Assert readable breakdowns are present
    breakdown_a = score_a["score_breakdown"]["components"]
    assert "pain" in breakdown_a
    assert "fit" in breakdown_a
    assert "timing" in breakdown_a
    assert "reachability" in breakdown_a
    assert "evidence" in breakdown_a

    # Lead A should have significant pain, high fit, high timing, high reachability
    assert breakdown_a["pain"]["score"] >= 15.0
    assert breakdown_a["fit"]["score"] == 25.0
    assert breakdown_a["reachability"]["score"] >= 18.0

    # Lead B should have near zero pain, reachability, timing
    breakdown_b = score_b["score_breakdown"]["components"]
    assert breakdown_b["pain"]["score"] == 0.0
    assert breakdown_b["reachability"]["score"] == 2.0  # website presence only

    # Obvious ranking check: A should beat B by at least 40 points
    assert score_a["final_score"] > 75.0
    assert score_b["final_score"] < 35.0
    assert (score_a["final_score"] - score_b["final_score"]) > 40.0


def test_changing_offer_profile_changes_fit():
    """Verify that modifying the Offer Profile directly modifies the Fit score and total score."""
    config = ScoringConfig()

    lead_features = {
        "category": "cafe",
        "rating": 3.8,
        "review_count": 50,
        "has_real_website": True,
        "website_is_https": True,
        "has_phone": True,
        "has_named_email": True,
        "has_generic_email": False,
        "hours_complete": True,
        "owner_reply_rate": 0.2,
        "negative_review_share": 0.1,
        "days_since_last_review": 30,
        "hex_opportunity_score": 75.0,
    }
    place = Place(
        name="Artisan Roastery",
        address="100 Feet Rd, Indiranagar, Bangalore",
        location=WKTElement("POINT(77.64 12.97)", srid=4326),
    )

    # 1. Profile tailored for cafes in Indiranagar
    profile_cafe = OfferProfile(
        name="Cafe Solutions",
        target_categories=["cafe"],
        min_rating=3.0,
        max_rating=4.5,
        target_regions=["Indiranagar"],
    )
    score_cafe_target = score_lead(lead_features, place, profile_cafe, config)

    # 2. Profile tailored for gym equipment in Whitefield
    profile_gym = OfferProfile(
        name="Gym Fitout Services",
        target_categories=["gym"],
        min_rating=4.5,
        max_rating=5.0,
        target_regions=["Whitefield"],
    )
    score_gym_target = score_lead(lead_features, place, profile_gym, config)

    fit_cafe = score_cafe_target["score_breakdown"]["components"]["fit"]["score"]
    fit_gym = score_gym_target["score_breakdown"]["components"]["fit"]["score"]

    # Cafe profile should yield full fit (25.0)
    assert fit_cafe == 25.0
    # Gym profile should yield 0.0 fit
    assert fit_gym == 0.0

    # Total score must reflect the difference
    assert score_cafe_target["final_score"] - score_gym_target["final_score"] == 25.0


def test_score_workspace_leads_end_to_end(db_session: Session, scoring_workspace: Workspace):
    """Verify that score_workspace_leads scores all places and persists records."""
    # Create 3 test places
    for i in range(3):
        place = Place(
            workspace_id=scoring_workspace.id,
            provider="gosom",
            provider_place_id=f"e2e-lead-{i}",
            name=f"Business {i}",
            category="cafe",
            normalized_category="cafe",
            address=f"Street {i}, Indiranagar, Bangalore",
            phone_e164=f"+91802222222{i}",
            rating=3.5 + (i * 0.4),
            review_count=30 * (i + 1),
            is_closed=False,
        )
        db_session.add(place)
    db_session.commit()

    scored = score_workspace_leads(db_session, scoring_workspace.id)
    assert scored == 3

    # Verify Lead records exist and have scores and breakdowns
    leads = (
        db_session.execute(select(Lead).where(Lead.workspace_id == scoring_workspace.id))
        .scalars()
        .all()
    )
    assert len(leads) == 3

    for lead in leads:
        assert lead.rule_score is not None
        assert 0.0 <= lead.rule_score <= 100.0
        assert lead.final_score == lead.rule_score
        assert "components" in lead.score_breakdown
        assert "pain" in lead.score_breakdown["components"]
        assert "fit" in lead.score_breakdown["components"]

        # Verify LeadFeature record was created
        feat = db_session.execute(
            select(LeadFeature).where(
                LeadFeature.lead_id == lead.id,
                LeadFeature.feature_version == FEATURE_VERSION,
            )
        ).scalar_one_or_none()
        assert feat is not None
        assert feat.features["category"] == "cafe"
        assert feat.features["review_count"] > 0
