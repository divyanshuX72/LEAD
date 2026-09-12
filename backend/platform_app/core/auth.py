"""
Authentication Core

JWT token management, password hashing, and FastAPI auth dependencies.
Multi-tenant: JWT payload includes company_id for data isolation.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.config.settings import get_settings
from platform_app.database.session import get_db_session
from platform_app.models.user import User
from platform_app.models.auth_models import Session as SessionModel

security_scheme = HTTPBearer(auto_error=False)


# ── Password Hashing ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT Token Management ────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    email: str,
    role: str,
    company_id: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str, datetime]:
    """
    Create a JWT access token.
    Returns (token, jti, expires_at).
    Includes company_id in payload for multi-tenant isolation.
    """
    settings = get_settings()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "company_id": company_id,
        "jti": jti,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str, datetime]:
    """
    Create a JWT refresh token.
    Returns (token, jti, expires_at).
    """
    settings = get_settings()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )

    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── FastAPI Dependencies ─────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency that extracts and validates the current user from JWT.
    Returns the User ORM object (with company relationship loaded).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Check if session/token is revoked
    jti = payload.get("jti")
    if jti:
        stmt = select(SessionModel).where(
            SessionModel.token_jti == jti,
            SessionModel.is_revoked == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    # Fetch user (company relationship loaded via selectin)
    stmt = select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Optional auth dependency — returns None if no token provided.
    Useful for public endpoints that behave differently when authenticated.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None
