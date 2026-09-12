"""
Authentication Schemas

Pydantic DTOs for auth endpoints.
Multi-tenant: includes company_name for registration and company_id in profile.
"""

from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ── Requests ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    remember_me: bool = False


class RegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(...)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Responses ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    company_id: str
    company_name: str = ""
    avatar_path: str | None = None
    is_active: bool
    email_verified: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    user: UserProfile | None = None
    tokens: TokenResponse | None = None
