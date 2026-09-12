"""
Company Model

Top-level tenant entity for multi-tenant data isolation.
Every data table references company_id for strict SaaS separation.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from platform_app.models.base import Base, TimestampMixin, generate_uuid


class Company(Base, TimestampMixin):
    """A company (tenant) on the platform."""
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
