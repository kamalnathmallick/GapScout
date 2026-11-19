"""FastAPI dependencies: database session, authentication, and tenant isolation."""

import time
import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.db import SessionLocal
from app.models import User, Workspace

security_bearer = HTTPBearer(auto_error=False)

# In-memory per-user sliding window rate limiter (requests, timestamp_window)
_RATE_LIMITS: dict[str, list[float]] = {}
RATE_LIMIT_MAX_PER_MINUTE = 120


def get_db() -> Iterator[Session]:
    """Yield a database session from the session factory."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Security(security_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate JWT access token and return the authenticated User."""
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.credentials
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not an access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        ) from None

    user = db.get(User, user_uuid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
        )

    return user


def get_current_workspace(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Workspace:
    """Enforce workspace tenant isolation.

    Returns the workspace associated with the current user. Every endpoint querying
    user data must depend on this to ensure zero cross-tenant leakage.
    """
    workspace = db.get(Workspace, user.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated workspace not found",
        )
    return workspace


def rate_limiter(user: Annotated[User, Depends(get_current_user)]) -> None:
    """Enforce per-user rate limit (120 requests/minute)."""
    now = time.time()
    user_key = str(user.id)
    timestamps = _RATE_LIMITS.setdefault(user_key, [])

    # Filter out requests older than 60 seconds
    valid_window = [t for t in timestamps if now - t < 60.0]
    if len(valid_window) >= RATE_LIMIT_MAX_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
        )

    valid_window.append(now)
    _RATE_LIMITS[user_key] = valid_window
