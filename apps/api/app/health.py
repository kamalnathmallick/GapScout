"""Health checks for the API, Postgres and Redis."""

import logging
import time
from collections.abc import Callable
from typing import Literal

import redis
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import get_settings
from app.db import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])

CheckStatus = Literal["ok", "error"]


class CheckResult(BaseModel):
    status: CheckStatus
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    checks: dict[str, CheckResult] = Field(default_factory=dict)


def _timed(fn: Callable[[], None]) -> CheckResult:
    start = time.perf_counter()
    try:
        fn()
    except Exception as exc:  # health checks must never raise
        logger.warning("health check failed: %s", type(exc).__name__)
        return CheckResult(status="error", detail=type(exc).__name__)
    latency = round((time.perf_counter() - start) * 1000, 2)
    return CheckResult(status="ok", latency_ms=latency)


def check_db() -> CheckResult:
    def _ping() -> None:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    return _timed(_ping)


def check_redis() -> CheckResult:
    def _ping() -> None:
        client = redis.Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            client.ping()
        finally:
            client.close()

    return _timed(_ping)


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "A dependency is unavailable"}},
)
def health(response: Response) -> HealthResponse:
    settings = get_settings()
    checks = {"db": check_db(), "redis": check_redis()}
    healthy = all(check.status == "ok" for check in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if healthy else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        checks=checks,
    )
