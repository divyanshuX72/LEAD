"""
Lead Agent Repositories — Multi-Tenant

All repositories filter by company_id for strict data isolation.
"""

from sqlalchemy import select, func, or_, and_, distinct, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.repositories.base import BaseRepository
from platform_app.models.lead_batch import LeadBatch
from platform_app.models.lead_batch_keyword import LeadBatchKeyword
from platform_app.models.lead import Lead
from platform_app.models.lead_source import LeadSource
from platform_app.models.export_job import ExportJob


class LeadBatchRepository(BaseRepository[LeadBatch]):
    def __init__(self, session: AsyncSession, company_id: str | None = None):
        super().__init__(LeadBatch, session)
        self.company_id = company_id

    async def get_all_ordered(self, limit: int = 100) -> list[LeadBatch]:
        stmt = (
            select(self.model)
            .where(self.model.company_id == self.company_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_batch_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.company_id == self.company_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, entity_id: str) -> LeadBatch | None:
        """Get batch by ID — scoped to company."""
        stmt = select(self.model).where(
            self.model.id == entity_id,
            self.model.company_id == self.company_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class LeadBatchKeywordRepository(BaseRepository[LeadBatchKeyword]):
    def __init__(self, session: AsyncSession):
        super().__init__(LeadBatchKeyword, session)

    async def get_by_batch(self, batch_id: str) -> list[LeadBatchKeyword]:
        stmt = (
            select(self.model)
            .where(self.model.batch_id == batch_id)
            .order_by(self.model.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession, company_id: str | None = None):
        super().__init__(Lead, session)
        self.company_id = company_id

    async def get_by_batch(
        self, batch_id: str, skip: int = 0, limit: int = 500
    ) -> list[Lead]:
        stmt = (
            select(self.model)
            .where(
                self.model.batch_id == batch_id,
                self.model.company_id == self.company_id,
            )
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_leads(self, skip: int = 0, limit: int = 500) -> list[Lead]:
        stmt = (
            select(self.model)
            .where(self.model.company_id == self.company_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_leads_by_batch_ids(self, batch_ids: list[str]) -> list[Lead]:
        stmt = (
            select(self.model)
            .where(
                self.model.batch_id.in_(batch_ids),
                self.model.company_id == self.company_id,
            )
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_total(self) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.company_id == self.company_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_batch(self, batch_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.batch_id == batch_id,
                self.model.company_id == self.company_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_unique_emails(self) -> int:
        from sqlalchemy import String, cast
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                func.json_length(self.model.emails) > 0,
                self.model.company_id == self.company_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_unique_phones(self) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                func.json_length(self.model.phones) > 0,
                self.model.company_id == self.company_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def find_duplicate_in_batch(
        self,
        batch_id: str,
        dedupe_key: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        business_name: str | None = None,
        city: str | None = None,
    ) -> Lead | None:
        """Find a duplicate lead within the same batch."""
        conditions = []

        if dedupe_key:
            conditions.append(self.model.dedupe_key == dedupe_key)
        if phone:
            from sqlalchemy import cast, String
            conditions.append(cast(self.model.phones, String).ilike(f"%{phone}%"))
        if email:
            from sqlalchemy import cast, String
            conditions.append(cast(self.model.emails, String).ilike(f"%{email}%"))

        if not conditions and business_name and city:
            conditions.append(and_(
                func.lower(self.model.business_name) == func.lower(business_name),
                func.lower(self.model.city) == func.lower(city),
            ))

        if not conditions:
            return None

        stmt = (
            select(self.model)
            .where(
                self.model.batch_id == batch_id,
                self.model.company_id == self.company_id,
                or_(*conditions),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, skip: int = 0, limit: int = 50) -> list[Lead]:
        stmt = (
            select(self.model)
            .where(
                self.model.company_id == self.company_id,
                or_(
                    self.model.business_name.ilike(f"%{query}%"),
                    cast(self.model.emails, String).ilike(f"%{query}%"),
                    cast(self.model.phones, String).ilike(f"%{query}%"),
                    self.model.city.ilike(f"%{query}%"),
                )
            )
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class LeadSourceRepository(BaseRepository[LeadSource]):
    def __init__(self, session: AsyncSession):
        super().__init__(LeadSource, session)

    async def get_by_lead(self, lead_id: str) -> list[LeadSource]:
        stmt = (
            select(self.model)
            .where(self.model.lead_id == lead_id)
            .order_by(self.model.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExportJobRepository(BaseRepository[ExportJob]):
    def __init__(self, session: AsyncSession, company_id: str | None = None):
        super().__init__(ExportJob, session)
        self.company_id = company_id

    async def get_recent(self, limit: int = 20) -> list[ExportJob]:
        stmt = (
            select(self.model)
            .where(self.model.company_id == self.company_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
