"""Schemas for workspace API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceCreateRequest(BaseModel):
    """Request body for creating a workspace."""

    name: str = Field(
        min_length=1,
        max_length=120,
        examples=["Demo Workspace"],
        description="Public-safe workspace display name.",
    )

    @field_validator("name")
    @classmethod
    def strip_and_validate_name(cls, value: str) -> str:
        """Trim workspace names and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("workspace name must not be blank")
        return stripped_value


class WorkspaceResponse(BaseModel):
    """Workspace representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
