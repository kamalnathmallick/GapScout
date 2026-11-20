"""Comprehensive integration tests for API v1 and strict workspace isolation."""

from unittest.mock import patch

import pytest
from geoalchemy2.elements import WKTElement
from starlette.testclient import TestClient

from app.main import app
from app.models import Lead, Place


@pytest.fixture
def api_client(db_engine):
    """TestClient that uses the test database via db_engine."""
    from sqlalchemy.orm import Session

    from app.api.deps import get_db

    def override_get_db():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. OpenAPI Documentation Verification
# ==============================================================================
def test_openapi_schema_contains_all_endpoints(api_client: TestClient):
    res = api_client.get("/openapi.json")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    schema = res.json()
    paths = schema["paths"]

    # Required v1 endpoints
    expected_endpoints = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/me",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/jobs/{job_id}/cancel",
        "/api/v1/jobs/{job_id}/resume",
        "/api/v1/places",
        "/api/v1/gap/{job_id}/hexes",
        "/api/v1/gap/{job_id}/summary",
        "/api/v1/leads",
        "/api/v1/leads/{lead_id}",
        "/api/v1/leads/{lead_id}/drafts",
        "/api/v1/leads/{lead_id}/events",
        "/api/v1/models",
        "/api/v1/models/active/metrics",
        "/api/v1/models/train",
        "/api/v1/offer-profile",
        "/api/v1/account/export",
        "/api/v1/account/data",
    ]

    for ep in expected_endpoints:
        assert ep in paths, f"Endpoint '{ep}' missing from OpenAPI specification!"


# ==============================================================================
# 2. Authentication Lifecycle Flow
# ==============================================================================
def test_auth_registration_login_refresh_flow(api_client: TestClient):
    # 1. Register
    reg_payload = {
        "email": "founder@startup.com",
        "password": "super-secure-password-123",
        "full_name": "Startup Founder",
        "workspace_name": "Startup HQ",
    }
    reg_res = api_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    tokens = reg_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["user"]["email"] == "founder@startup.com"
    assert tokens["user"]["workspace"]["name"] == "Startup HQ"

    # Duplicate registration fails
    dup_res = api_client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

    # 2. Login
    login_res = api_client.post(
        "/api/v1/auth/login",
        json={"email": "founder@startup.com", "password": "super-secure-password-123"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
    refresh_token = login_res.json()["refresh_token"]

    # Wrong password fails
    bad_login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "founder@startup.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    # 3. Refresh token rotation
    ref_res = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert "access_token" in new_tokens
    new_access_token = new_tokens["access_token"]

    # 4. Profile /me
    me_res = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert me_res.status_code == 200
    me = me_res.json()
    assert me["email"] == "founder@startup.com"
    assert me["workspace"]["name"] == "Startup HQ"


# ==============================================================================
# 3. Jobs: Dry-Run Estimation and Lifecycle
# ==============================================================================
def test_jobs_dry_run_and_execution(api_client: TestClient):
    # Register user
    reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "jobs_tester@test.com",
            "password": "password123456",
            "workspace_name": "Jobs WS",
        },
    ).json()
    auth_header = {"Authorization": f"Bearer {reg['access_token']}"}

    # 1. Dry run
    dry_run_payload = {
        "category": "bakery",
        "area_name": "Indiranagar",
        "bbox": {
            "min_lat": 12.960,
            "min_lon": 77.630,
            "max_lat": 12.980,
            "max_lon": 77.650,
        },
        "cell_size_m": 1000.0,
        "dry_run": True,
    }
    dry_res = api_client.post("/api/v1/jobs", json=dry_run_payload, headers=auth_header)
    assert dry_res.status_code == 201
    dry_data = dry_res.json()
    assert "cells_total" in dry_data
    assert dry_data["cells_total"] > 0
    assert "area_km2" in dry_data

    # 2. Create actual job (mock dispatch to prevent external scrape during test)
    with patch("app.api.v1.jobs.dispatch_job_cells"):
        real_payload = {**dry_run_payload, "dry_run": False}
        job_res = api_client.post("/api/v1/jobs", json=real_payload, headers=auth_header)
        assert job_res.status_code == 201
        job_data = job_res.json()
        job_id = job_data["id"]
        assert job_data["category"] == "bakery"
        assert job_data["status"] == "pending"

    # 3. Get job progress
    prog_res = api_client.get(f"/api/v1/jobs/{job_id}", headers=auth_header)
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["job_id"] == job_id
    assert prog_data["cells_total"] == dry_data["cells_total"]

    # 4. Cancel job
    cancel_res = api_client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_header)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


# ==============================================================================
# 4. Strict Workspace Tenant Isolation (User A vs User B)
# ==============================================================================
def test_workspace_isolation_user_a_cannot_access_user_b_data(api_client: TestClient, db_session):
    # 1. Register User A in Workspace A
    res_a = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "usera@alpha.com",
            "password": "passwordA12345",
            "workspace_name": "Workspace Alpha",
        },
    ).json()
    token_a = res_a["access_token"]
    ws_id_a = res_a["user"]["workspace"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B in Workspace B
    res_b = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "userb@beta.com",
            "password": "passwordB12345",
            "workspace_name": "Workspace Beta",
        },
    ).json()
    token_b = res_b["access_token"]
    ws_id_b = res_b["user"]["workspace"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert ws_id_a != ws_id_b

    # 3. Create a private place in Workspace A directly
    place_a = Place(
        workspace_id=ws_id_a,
        provider="test",
        provider_place_id="alpha_secret_place",
        name="Alpha Private Bakery",
        category="bakery",
        normalized_category="cafe",
        rating=4.8,
        review_count=100,
        location=WKTElement("POINT(77.64 12.97)", srid=4326),
        raw={"secret": "alpha_proprietary_data"},
    )
    db_session.add(place_a)
    db_session.commit()

    # 4. Create a search job for Workspace A
    with patch("app.api.v1.jobs.dispatch_job_cells"):
        job_res = api_client.post(
            "/api/v1/jobs",
            json={
                "category": "bakery",
                "area_name": "Alpha Area",
                "bbox": {"min_lat": 12.96, "min_lon": 77.63, "max_lat": 12.98, "max_lon": 77.65},
                "dry_run": False,
            },
            headers=headers_a,
        )
        job_a_id = job_res.json()["id"]

    # ==========================================================================
    # TENANT ISOLATION CHECKS: User B MUST NOT be able to see User A's data!
    # ==========================================================================

    # 1. User B querying places: User A's place must NOT appear
    places_b_res = api_client.get("/api/v1/places", headers=headers_b)
    assert places_b_res.status_code == 200
    places_b_data = places_b_res.json()
    assert places_b_data["pagination"]["total"] == 0
    assert len(places_b_data["items"]) == 0

    # User A querying places: User A sees their own place
    places_a_res = api_client.get("/api/v1/places", headers=headers_a)
    assert places_a_res.status_code == 200
    places_a_data = places_a_res.json()
    assert places_a_data["pagination"]["total"] == 1
    assert places_a_data["items"][0]["name"] == "Alpha Private Bakery"

    # 2. User B querying User A's job details: MUST 404
    job_b_inspect = api_client.get(f"/api/v1/jobs/{job_a_id}", headers=headers_b)
    assert job_b_inspect.status_code == 404

    # 3. User B attempting to cancel User A's job: MUST 404
    job_b_cancel = api_client.post(f"/api/v1/jobs/{job_a_id}/cancel", headers=headers_b)
    assert job_b_cancel.status_code == 404

    # 4. User B querying User A's gap hexes: MUST 404
    gap_b_inspect = api_client.get(f"/api/v1/gap/{job_a_id}/hexes", headers=headers_b)
    assert gap_b_inspect.status_code == 404


# ==============================================================================
# 5. Leads, Outreach Drafts, and Outreach Events Flow
# ==============================================================================
def test_leads_outreach_workflow(api_client: TestClient, db_session):
    # Register
    reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "leads_agent@test.com",
            "password": "password123456",
            "workspace_name": "Outreach WS",
        },
    ).json()
    token = reg["access_token"]
    ws_id = reg["user"]["workspace"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add place and lead in DB
    place = Place(
        workspace_id=ws_id,
        provider="test",
        provider_place_id="lead_place_1",
        name="Artisan Cafe Indiranagar",
        category="cafe",
        normalized_category="cafe",
        email="owner@artisancafe.com",
        phone_e164="+918025251111",
        rating=3.9,
        review_count=80,
        location=WKTElement("POINT(77.6412 12.9715)", srid=4326),
    )
    db_session.add(place)
    db_session.flush()

    lead = Lead(
        workspace_id=ws_id,
        place_id=place.id,
        status="new",
        rule_score=82.5,
        final_score=82.5,
        score_breakdown={"pain": 25, "fit": 25, "timing": 15, "reachability": 17.5},
        notes="High potential lead.",
    )
    db_session.add(lead)
    db_session.commit()

    # 1. List leads with filter
    leads_res = api_client.get("/api/v1/leads?min_score=80.0&has_email=true", headers=headers)
    assert leads_res.status_code == 200
    leads_data = leads_res.json()
    assert leads_data["pagination"]["total"] == 1
    lead_item = leads_data["items"][0]
    assert lead_item["final_score"] == 82.5
    assert lead_item["place"]["name"] == "Artisan Cafe Indiranagar"

    # 2. Update status and notes
    patch_res = api_client.patch(
        f"/api/v1/leads/{lead.id}",
        json={"status": "shortlisted", "notes": "Reviewed by marketing team."},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "shortlisted"
    assert patch_res.json()["notes"] == "Reviewed by marketing team."

    # 3. Create outreach draft
    draft_res = api_client.post(
        f"/api/v1/leads/{lead.id}/drafts",
        json={"channel": "email", "body": "Hi there, loved your cafe! Saw some feedback..."},
        headers=headers,
    )
    assert draft_res.status_code == 201
    assert draft_res.json()["channel"] == "email"

    # 4. Record outreach event
    event_res = api_client.post(
        f"/api/v1/leads/{lead.id}/events",
        json={"event_type": "contacted", "features_snapshot": {"score": 82.5}},
        headers=headers,
    )
    assert event_res.status_code == 201
    assert event_res.json()["event_type"] == "contacted"


# ==============================================================================
# 6. Account Data Export and Deletion
# ==============================================================================
def test_account_export_and_data_deletion(api_client: TestClient):
    reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "delete_me@test.com",
            "password": "password123456",
            "workspace_name": "Temporary WS",
        },
    ).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Export data
    export_res = api_client.get("/api/v1/account/export", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["export_metadata"]["user_email"] == "delete_me@test.com"

    # 2. Delete data (Right to be forgotten)
    del_res = api_client.delete("/api/v1/account/data", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 3. Authenticated requests now fail (workspace and user deleted)
    check_res = api_client.get("/api/v1/auth/me", headers=headers)
    assert check_res.status_code == 401


# ==============================================================================
# 7. Offer Profile Endpoints
# ==============================================================================
def test_offer_profile_lifecycle(api_client: TestClient):
    reg = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "offer_profile_user@test.com",
            "password": "password123456",
            "workspace_name": "Offer WS",
        },
    ).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get default offer profile
    get_res = api_client.get("/api/v1/offer-profile", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["name"] == "Default Offer"
    assert data["target_categories"] == []

    # 2. Update offer profile
    update_res = api_client.patch(
        "/api/v1/offer-profile",
        json={
            "name": "B2B SaaS Outreach",
            "offer_description": "We sell automated local SEO and reputation management",
            "target_categories": ["cafe", "restaurant"],
            "min_rating": 2.5,
            "max_rating": 4.2,
            "target_regions": ["Indiranagar", "Koramangala"],
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["name"] == "B2B SaaS Outreach"
    assert updated["target_categories"] == ["cafe", "restaurant"]
    assert updated["min_rating"] == 2.5
    assert updated["max_rating"] == 4.2
    assert "Indiranagar" in updated["target_regions"]
