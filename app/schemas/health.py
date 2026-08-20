from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for basic API health endpoint response."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})


class DatabaseHealthResponse(BaseModel):
    """Schema for database health check endpoint response."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})
    database: str = Field(..., json_schema_extra={"example": "connected"})
