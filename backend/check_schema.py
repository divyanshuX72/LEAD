import asyncio
import os
from sqlalchemy import create_engine, text
from platform_app.config.settings import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_SYNC_URL)

with engine.connect() as conn:
    try:
        result = conn.execute(text("SHOW CREATE TABLE leads;"))
        print("Leads Table:")
        for row in result:
            print(row[1])
    except Exception as e:
        print(f"Error reading leads: {e}")

    try:
        result2 = conn.execute(text("SHOW CREATE TABLE lead_batches;"))
        print("\nLead Batches Table:")
        for row in result2:
            print(row[1])
    except Exception as e:
        print(f"Error reading lead_batches: {e}")
