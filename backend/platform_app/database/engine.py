"""
Database Engine Configuration

Async SQLAlchemy engine for MySQL via aiomysql.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from platform_app.config.settings import get_settings

settings = get_settings()

# Async engine for application use
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 10},
)

# Async session factory
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 10},
)
