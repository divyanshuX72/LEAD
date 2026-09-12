import os
import sys
from logging.config import fileConfig

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from platform_app.config.settings import get_settings
from platform_app.models.base import Base

import platform_app.models.workspace
import platform_app.models.user
import platform_app.models.company
import platform_app.models.auth_models
import platform_app.models.lead_batch
import platform_app.models.lead_batch_keyword
import platform_app.models.lead
import platform_app.models.lead_source
import platform_app.models.export_job
import platform_app.models.search_history

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the one from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
