"""
Database Initialization — Lead Agent

Creates the MySQL database and all tables if they don't exist.
"""

import pymysql
from platform_app.config.settings import get_settings
from platform_app.database.engine import sync_engine


def create_database_if_not_exists():
    """Create the lead database if it doesn't exist."""
    try:
        settings = get_settings()
        # Parse connection details from DATABASE_SYNC_URL
        from urllib.parse import urlparse, unquote
        parsed = urlparse(settings.DATABASE_SYNC_URL)
        
        connection = pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=unquote(parsed.password) if parsed.password else "",
            charset="utf8mb4",
        )
        db_name = parsed.path.lstrip("/")
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.close()
        print(f"[OK] Database '{db_name}' ready")
    except Exception as e:
        print(f"[ERROR] Database creation failed: {e}")
        raise


def create_tables():
    """Create all tables from ORM models."""
    from platform_app.models.base import Base
    # Import all models to register them with Base
    import platform_app.models.company  # noqa
    import platform_app.models.workspace  # noqa
    import platform_app.models.user  # noqa
    import platform_app.models.auth_models  # noqa
    # Lead Agent models
    import platform_app.models.lead_batch  # noqa
    import platform_app.models.lead_batch_keyword  # noqa
    import platform_app.models.lead  # noqa
    import platform_app.models.lead_source  # noqa
    import platform_app.models.export_job  # noqa

    Base.metadata.create_all(bind=sync_engine)
    print("[OK] All tables created")


def init_database():
    """Full database initialization."""
    create_database_if_not_exists()
    create_tables()
