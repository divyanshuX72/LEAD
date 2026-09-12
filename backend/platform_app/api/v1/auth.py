"""
Authentication Router

REST API endpoints for auth operations.
Multi-tenant: register creates a company, profile includes company info.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.database.session import get_db_session
from platform_app.core.auth import get_current_user, decode_token
from platform_app.models.user import User
from platform_app.services.auth_service import AuthService
from platform_app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    RefreshTokenRequest,
    AuthResponse,
    UserProfile,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(session)


def _user_to_profile(user: User) -> UserProfile:
    """Convert User ORM object to UserProfile DTO with company info."""
    return UserProfile(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        company_id=user.company_id,
        company_name=user.company.name if user.company else "",
        avatar_path=user.avatar_path,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/register", response_model=AuthResponse)
async def register(
    data: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Register a new company and admin user account."""
    result = await auth_service.register(
        company_name=data.company_name,
        name=data.name,
        email=data.email,
        password=data.password,
        confirm_password=data.confirm_password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return AuthResponse(
        success=True,
        message="Registration successful",
        user=_user_to_profile(result["user"]),
        tokens=TokenResponse(**result["tokens"]),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Authenticate user and return JWT tokens."""
    result = await auth_service.login(
        email=data.email,
        password=data.password,
        remember_me=data.remember_me,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return AuthResponse(
        success=True,
        message="Login successful",
        user=_user_to_profile(result["user"]),
        tokens=TokenResponse(**result["tokens"]),
    )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Revoke all tokens for the current user."""
    await auth_service.logout(user_id=user.id)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Refresh access token using a refresh token."""
    tokens = await auth_service.refresh_tokens(
        refresh_token_str=data.refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(**tokens)


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Initiate password reset flow."""
    result = await auth_service.forgot_password(email=data.email)
    return {"success": True, **result}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Reset password with a reset token."""
    await auth_service.reset_password(
        token=data.token,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )
    return {"success": True, "message": "Password reset successful"}


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(_get_auth_service),
):
    """Change password for the currently authenticated user."""
    await auth_service.change_password(
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )
    return {"success": True, "message": "Password changed successfully. Please log in again."}


@router.get("/me", response_model=UserProfile)
async def get_current_profile(user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return _user_to_profile(user)
