"""Auth endpoints: register, login, refresh, me."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User, Workspace
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    WorkspaceOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_response(user: User, workspace: Workspace) -> TokenResponse:
    token_data = {"sub": str(user.id), "workspace_id": str(workspace.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    ws_out = WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )
    user_out = UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        workspace=ws_out,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_out,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Register a new user and workspace."""
    # Check if email is already taken
    existing = db.scalar(select(User).where(User.email == req.email.lower().strip()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # 1. Create workspace
    workspace = Workspace(name=req.workspace_name)
    db.add(workspace)
    db.flush()

    # 2. Hash password with Argon2 and create user
    hashed_pw = hash_password(req.password)
    user = User(
        workspace_id=workspace.id,
        email=req.email.lower().strip(),
        password_hash=hashed_pw,
        full_name=req.full_name,
        role="owner",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(workspace)

    return _build_token_response(user, workspace)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Log in with email and password."""
    user = db.scalar(select(User).where(User.email == req.email.lower().strip()))
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    workspace = db.get(Workspace, user.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return _build_token_response(user, workspace)


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Rotate refresh token and issue a fresh access token."""
    try:
        payload = decode_token(req.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from None

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = db.get(User, user_id_str)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    workspace = db.get(Workspace, user.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return _build_token_response(user, workspace)


@router.get("/me", response_model=UserOut)
def me(
    user: Annotated[User, Depends(get_current_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
) -> UserOut:
    """Get profile of current authenticated user and workspace."""
    ws_out = WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        workspace=ws_out,
        created_at=user.created_at,
    )
