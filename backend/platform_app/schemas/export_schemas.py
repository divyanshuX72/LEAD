"""
Export Schemas

Pydantic DTOs for the export pipeline.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    name: str = Field(..., description="Name of the export file")
    format: str = Field(..., description="Format: csv, xlsx, json, pdf")
    filters: dict | None = Field(None, description="Filters to apply to the leads query")
    columns: list[str] | None = Field(None, description="Specific columns to include")


class ExportJobResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    format: str
    status: str
    total_rows: int
    file_size_bytes: int
    download_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
