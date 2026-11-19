from fastapi.testclient import TestClient

import app.health as health_module
from app.health import CheckResult
from app.main import app

client = TestClient(app)


def _fake_checks(monkeypatch, db_ok: bool, redis_ok: bool) -> None:
    monkeypatch.setattr(
        health_module,
        "check_db",
        lambda: CheckResult(status="ok" if db_ok else "error", latency_ms=1.5),
    )
    monkeypatch.setattr(
        health_module,
        "check_redis",
        lambda: CheckResult(status="ok" if redis_ok else "error", latency_ms=0.4),
    )


def test_health_reports_ok_when_dependencies_are_up(monkeypatch) -> None:
    _fake_checks(monkeypatch, db_ok=True, redis_ok=True)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == {"status": "ok", "latency_ms": 1.5, "detail": None}
    assert body["checks"]["redis"]["status"] == "ok"


def test_health_reports_503_when_db_is_down(monkeypatch) -> None:
    _fake_checks(monkeypatch, db_ok=False, redis_ok=True)

    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"]["status"] == "error"
    assert body["checks"]["redis"]["status"] == "ok"


def test_timed_check_never_leaks_exception_message() -> None:
    def boom() -> None:
        raise RuntimeError("password=secret")

    result = health_module._timed(boom)

    assert result.status == "error"
    assert result.detail == "RuntimeError"
    assert "secret" not in result.model_dump_json()


def test_root_returns_service_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
