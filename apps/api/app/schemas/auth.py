"""Authentication request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, description="Password (at least 8 characters)")
    full_name: str | None = None
    workspace_name: str = Field(default="My Workspace", min_length=2)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class WorkspaceOut(BaseModel):
    """Workspace details."""

    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    """User details."""

    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool = False
    workspace: WorkspaceOut
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT Token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class VerifyEmailRequest(BaseModel):
    """Request email verification link."""

    email: EmailStr | None = None


class VerifyEmailConfirm(BaseModel):
    """Confirm email verification token."""

    token: str


class ForgotPasswordRequest(BaseModel):
    """Request password reset link."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with token."""

    token: str
    new_password: str = Field(min_length=8)
