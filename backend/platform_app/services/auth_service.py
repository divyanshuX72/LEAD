"""
Authentication Service

Business logic for user registration, login, logout, password management.
Multi-tenant: registration creates a Company, user tokens include company_id.
"""

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.models.user import User
from platform_app.models.company import Company
from platform_app.models.auth_models import Session as SessionModel
from platform_app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from platform_app.config.settings import get_settings
from platform_app.core.exceptions import ValidationException, AppException


class AuthService:
    """Handles all authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        company_name: str,
        name: str,
        email: str,
        password: str,
        confirm_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Register a new company and admin user account."""
        # Validate passwords match
        if password != confirm_password:
            raise ValidationException("Passwords do not match")

        # Validate password strength
        self._validate_password_strength(password)

        # Validate email format
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            raise ValidationException("Invalid email format")

        # Validate company name
        if not company_name or len(company_name.strip()) < 2:
            raise ValidationException("Company name must be at least 2 characters")

        # Check if email already exists
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationException("Email is already registered")

        # 1. Create company
        company = Company(
            name=company_name.strip(),
            email=email.lower().strip(),
        )
        self.session.add(company)
        await self.session.flush()

        # 2. Create admin user linked to company
        user = User(
            company_id=company.id,
            name=name,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
            email_verified=False,
        )
        self.session.add(user)
        await self.session.flush()

        # 3. Generate tokens (with company_id in JWT)
        access_token, access_jti, access_expires = create_access_token(
            user_id=user.id, email=user.email, role=user.role,
            company_id=company.id,
        )
        refresh_token, refresh_jti, refresh_expires = create_refresh_token(
            user_id=user.id
        )

        # Store sessions
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=access_jti,
            token_type="access",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=access_expires,
        ))
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=refresh_jti,
            token_type="refresh",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_expires,
        ))

        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        await self.session.refresh(company)

        settings = get_settings()
        return {
            "user": user,
            "company": company,
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        }

    async def login(
        self,
        email: str,
        password: str,
        remember_me: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Authenticate a user and return tokens with company_id."""
        # Find user
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise AppException(status_code=401, message="Invalid email or password")

        if not user.is_active:
            raise AppException(status_code=403, message="Account is disabled")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise AppException(status_code=401, message="Invalid email or password")

        # Generate tokens (with company_id)
        access_token, access_jti, access_expires = create_access_token(
            user_id=user.id, email=user.email, role=user.role,
            company_id=user.company_id,
        )
        refresh_token, refresh_jti, refresh_expires = create_refresh_token(
            user_id=user.id
        )

        # Store sessions
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=access_jti,
            token_type="access",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=access_expires,
        ))
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=refresh_jti,
            token_type="refresh",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_expires,
        ))

        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)

        settings = get_settings()
        return {
            "user": user,
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        }

    async def logout(self, user_id: str, token_jti: str | None = None) -> None:
        """Revoke all active sessions or a specific token."""
        if token_jti:
            stmt = select(SessionModel).where(
                SessionModel.user_id == user_id,
                SessionModel.token_jti == token_jti,
            )
        else:
            stmt = select(SessionModel).where(
                SessionModel.user_id == user_id,
                SessionModel.is_revoked == False,  # noqa: E712
            )

        result = await self.session.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.is_revoked = True
        await self.session.commit()

    async def refresh_tokens(
        self,
        refresh_token_str: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Use a refresh token to get new access + refresh tokens."""
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise AppException(status_code=401, message="Invalid refresh token")

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Check if refresh token is revoked
        stmt = select(SessionModel).where(
            SessionModel.token_jti == jti,
        )
        result = await self.session.execute(stmt)
        session_record = result.scalar_one_or_none()

        if not session_record or session_record.is_revoked:
            raise AppException(status_code=401, message="Refresh token is invalid or revoked")

        # Revoke old refresh token
        session_record.is_revoked = True

        # Get user
        stmt = select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AppException(status_code=401, message="User not found or inactive")

        # Generate new tokens (with company_id)
        access_token, access_jti, access_expires = create_access_token(
            user_id=user.id, email=user.email, role=user.role,
            company_id=user.company_id,
        )
        new_refresh_token, refresh_jti, refresh_expires = create_refresh_token(
            user_id=user.id
        )

        # Store new sessions
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=access_jti,
            token_type="access",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=access_expires,
        ))
        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=refresh_jti,
            token_type="refresh",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_expires,
        ))

        await self.session.commit()

        settings = get_settings()
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        """Change the user's password."""
        if new_password != confirm_password:
            raise ValidationException("Passwords do not match")

        self._validate_password_strength(new_password)

        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise AppException(status_code=400, message="Current password is incorrect")

        user.password_hash = hash_password(new_password)

        # Revoke all sessions (force re-login)
        stmt = select(SessionModel).where(
            SessionModel.user_id == user.id,
            SessionModel.is_revoked == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        for s in result.scalars().all():
            s.is_revoked = True

        await self.session.commit()

    async def forgot_password(self, email: str) -> dict:
        """
        Initiate password reset flow.
        Architecture-ready: creates reset token but doesn't send email.
        """
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        # Always return success to prevent email enumeration
        if not user:
            return {"message": "If an account with that email exists, a reset link has been sent."}

        # Generate a reset token (stored as a refresh-type token with short expiry)
        from datetime import timedelta
        reset_token, reset_jti, reset_expires = create_refresh_token(
            user_id=user.id,
            expires_delta=timedelta(hours=1),
        )

        self.session.add(SessionModel(
            user_id=user.id,
            token_jti=reset_jti,
            token_type="reset",
            expires_at=reset_expires,
        ))
        await self.session.commit()

        # In production, send email with reset_token
        # For now, return the token (dev mode only)
        settings = get_settings()
        result_data = {"message": "If an account with that email exists, a reset link has been sent."}
        if settings.DEBUG:
            result_data["reset_token"] = reset_token
        return result_data

    async def reset_password(
        self, token: str, new_password: str, confirm_password: str
    ) -> None:
        """Reset password using a reset token."""
        if new_password != confirm_password:
            raise ValidationException("Passwords do not match")

        self._validate_password_strength(new_password)

        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise AppException(status_code=400, message="Invalid reset token")

        jti = payload.get("jti")
        user_id = payload.get("sub")

        # Verify the reset session exists and isn't revoked
        stmt = select(SessionModel).where(
            SessionModel.token_jti == jti,
            SessionModel.token_type == "reset",
        )
        result = await self.session.execute(stmt)
        session_record = result.scalar_one_or_none()

        if not session_record or session_record.is_revoked:
            raise AppException(status_code=400, message="Invalid or expired reset token")

        # Revoke the reset token
        session_record.is_revoked = True

        # Update password
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AppException(status_code=400, message="User not found")

        user.password_hash = hash_password(new_password)

        # Revoke all other sessions
        stmt = select(SessionModel).where(
            SessionModel.user_id == user.id,
            SessionModel.is_revoked == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        for s in result.scalars().all():
            s.is_revoked = True

        await self.session.commit()

    def _validate_password_strength(self, password: str) -> None:
        """Enforce password policy."""
        if len(password) < 8:
            raise ValidationException("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", password):
            raise ValidationException("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            raise ValidationException("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", password):
            raise ValidationException("Password must contain at least one digit")
