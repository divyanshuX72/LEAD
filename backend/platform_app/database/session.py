"""
Database Session Management

Provides async session dependency for FastAPI injection.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from platform_app.database.engine import AsyncSessionFactory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Session is automatically closed after the request completes.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
