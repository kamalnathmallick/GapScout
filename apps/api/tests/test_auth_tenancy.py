"""Tests for Prompt 16:
Auth verification, password reset, workspace isolation, settings, and deletion.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.auth.security import hash_password, verify_password
from app.main import app
from app.models import Lead, Place, SearchJob, User, Workspace


@pytest.fixture
def tenancy_setup(db_session):
    """Seed two isolated workspaces with users and resources."""
    u_suffix = uuid.uuid4().hex[:6]
    # Workspace A
    ws_a = Workspace(
        name=f"Workspace Alpha {u_suffix}",
        max_cells_per_job=200,
        daily_llm_cost_cap_usd=5.0,
    )
    db_session.add(ws_a)
    db_session.flush()

    user_a = User(
        workspace_id=ws_a.id,
        email=f"alice_{u_suffix}@alpha.example.com",
        password_hash=hash_password("PasswordAlpha123!"),
        full_name="Alice Alpha",
        role="owner",
        is_active=True,
    )
    db_session.add(user_a)

    place_a = Place(
        workspace_id=ws_a.id,
        provider="fake",
        provider_place_id=f"pl_{uuid.uuid4().hex[:8]}",
        name="Alpha Cafe",
        review_count=45,
        rating=4.5,
        email="owner@alphacafe.com",
    )
    db_session.add(place_a)
    db_session.flush()

    lead_a = Lead(
        workspace_id=ws_a.id,
        place_id=place_a.id,
        status="new",
        rule_score=80.0,
        final_score=80.0,
    )
    db_session.add(lead_a)

    job_a = SearchJob(
        workspace_id=ws_a.id,
        category="cafe",
        area_name="Downtown",
        status="completed",
        params={},
    )
    db_session.add(job_a)

    # Workspace B
    ws_b = Workspace(name=f"Workspace Beta {u_suffix}", max_cells_per_job=100)
    db_session.add(ws_b)
    db_session.flush()

    user_b = User(
        workspace_id=ws_b.id,
        email=f"bob_{u_suffix}@beta.example.com",
        password_hash=hash_password("PasswordBeta123!"),
        full_name="Bob Beta",
        role="owner",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()

    return {
        "ws_a": ws_a,
        "user_a": user_a,
        "place_a": place_a,
        "lead_a": lead_a,
        "job_a": job_a,
        "ws_b": ws_b,
        "user_b": user_b,
    }


def test_email_verification_flow(db_session, tenancy_setup):
    """Verify email verification token request and confirmation."""
    user = tenancy_setup["user_a"]
    client = TestClient(app)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 1. Request verification
        req_res = client.post("/api/v1/auth/verify-email/request", json={"email": user.email})
        assert req_res.status_code == 200
        db_session.refresh(user)
        assert user.verification_token is not None

        # 2. Confirm verification with valid token
        confirm_res = client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": user.verification_token},
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["is_verified"] is True
        db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None

        # 3. Confirming invalid token fails
        bad_res = client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": "invalid_token_123"},
        )
        assert bad_res.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_password_reset_flow(db_session, tenancy_setup):
    """Verify password reset request, expiration check, and password update."""
    user = tenancy_setup["user_b"]
    client = TestClient(app)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 1. Request password reset
        req_res = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
        assert req_res.status_code == 200
        db_session.refresh(user)
        assert user.reset_token is not None
        assert user.reset_token_expires_at is not None

        # 2. Reset password with valid token
        reset_res = client.post(
            "/api/v1/auth/reset-password",
            json={"token": user.reset_token, "new_password": "NewSecretPassword99!"},
        )
        assert reset_res.status_code == 200
        db_session.refresh(user)
        assert verify_password("NewSecretPassword99!", user.password_hash)
        assert user.reset_token is None

        # 3. Reset password with expired token fails
        user.reset_token = "expired_tok"
        user.reset_token_expires_at = datetime.now(UTC) - timedelta(minutes=10)
        db_session.commit()

        expired_res = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "expired_tok", "new_password": "AnotherPassword123!"},
        )
        assert expired_res.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_workspace_isolation_cross_tenant_checks(db_session, tenancy_setup):
    """Prove strict multi-tenant isolation: User B cannot access Workspace A's records."""
    ws_b = tenancy_setup["ws_b"]
    user_b = tenancy_setup["user_b"]
    lead_a = tenancy_setup["lead_a"]
    job_a = tenancy_setup["job_a"]

    client = TestClient(app)
    app.dependency_overrides[get_current_workspace] = lambda: ws_b
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # User B trying to access Lead A
        lead_res = client.get(f"/api/v1/leads/{lead_a.id}")
        assert lead_res.status_code == 404

        # User B trying to generate draft for Lead A
        draft_res = client.post(
            f"/api/v1/leads/{lead_a.id}/generate-draft",
            json={"channel": "email"},
        )
        assert draft_res.status_code == 404

        # User B trying to view SearchJob A
        job_res = client.get(f"/api/v1/jobs/{job_a.id}")
        assert job_res.status_code == 404

        # User B export should only export Workspace B records (0 places, 0 leads)
        export_res = client.get("/api/v1/account/export?format=json")
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert export_data["places_count"] == 0
        assert export_data["leads_count"] == 0
        assert export_data["export_metadata"]["workspace_id"] == str(ws_b.id)
    finally:
        app.dependency_overrides.clear()


def test_settings_workspace_caps_and_scoring_weights(db_session, tenancy_setup):
    """Verify settings endpoints: caps update and scoring weights editor with reset."""
    ws_a = tenancy_setup["ws_a"]
    user_a = tenancy_setup["user_a"]

    client = TestClient(app)
    app.dependency_overrides[get_current_workspace] = lambda: ws_a
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 1. Workspace Caps GET & PUT
        caps_get = client.get("/api/v1/settings/workspace-caps")
        assert caps_get.status_code == 200
        assert caps_get.json()["max_cells_per_job"] == 200

        caps_put = client.put(
            "/api/v1/settings/workspace-caps",
            json={"max_cells_per_job": 350, "daily_llm_cost_cap_usd": 10.0},
        )
        assert caps_put.status_code == 200
        assert caps_put.json()["max_cells_per_job"] == 350
        assert caps_put.json()["daily_llm_cost_cap_usd"] == 10.0

        # 2. Scoring Weights GET, PUT, RESET
        weights_get = client.get("/api/v1/settings/scoring-weights")
        assert weights_get.status_code == 200
        assert weights_get.json()["weights"]["pain"] == 25.0

        weights_put = client.put(
            "/api/v1/settings/scoring-weights",
            json={
                "weights": {
                    "pain": 40.0,
                    "fit": 20.0,
                    "timing": 10.0,
                    "reachability": 20.0,
                    "evidence": 10.0,
                }
            },
        )
        assert weights_put.status_code == 200
        assert weights_put.json()["is_custom"] is True
        assert weights_put.json()["weights"]["pain"] == 40.0

        weights_reset = client.post("/api/v1/settings/scoring-weights/reset")
        assert weights_reset.status_code == 200
        assert weights_reset.json()["is_custom"] is False
        assert weights_reset.json()["weights"]["pain"] == 25.0

        # 3. API Usage
        usage_res = client.get("/api/v1/settings/api-usage")
        assert usage_res.status_code == 200
        assert "total_cost_usd" in usage_res.json()
    finally:
        app.dependency_overrides.clear()


def test_account_export_and_irreversible_deletion(db_session, tenancy_setup):
    """Verify JSON/CSV export and confirmation-guarded permanent account deletion."""
    ws_a = tenancy_setup["ws_a"]
    ws_a_id = ws_a.id
    place_a_id = tenancy_setup["place_a"].id
    lead_a_id = tenancy_setup["lead_a"].id
    user_a = tenancy_setup["user_a"]

    client = TestClient(app)
    app.dependency_overrides[get_current_workspace] = lambda: ws_a
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 1. CSV export
        csv_res = client.get("/api/v1/account/export?format=csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "Alpha Cafe" in csv_res.text
        assert "record_type,id,name_or_category" in csv_res.text

        # 2. Delete with invalid confirmation rejected
        bad_del = client.request(
            "DELETE",
            "/api/v1/account/data",
            json={"confirmation": "WRONG_PHRASE"},
        )
        assert bad_del.status_code == 400

        # 3. Delete with valid confirmation executes cascade deletion
        del_res = client.request(
            "DELETE",
            "/api/v1/account/data",
            json={"confirmation": "DELETE MY DATA"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # Workspace A and related records must be gone
        assert db_session.get(Workspace, ws_a_id) is None
        assert db_session.get(Place, place_a_id) is None
        assert db_session.get(Lead, lead_a_id) is None
    finally:
        app.dependency_overrides.clear()
