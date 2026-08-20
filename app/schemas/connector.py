import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateConnectorRequest(BaseModel):
    """Schema for creating a platform data connector definition."""

    name: str = Field(..., description="Unique connector identifier name (e.g. 'sales-db').")
    connector_type: str = Field(..., description="Connector type (e.g. postgresql, mysql, mssql, mongodb, s3).")
    category: str = Field(..., description="Connector category (e.g. RELATIONAL_DATABASE, NOSQL_DATABASE, OBJECT_STORAGE).")
    configuration: dict[str, Any] = Field(..., description="Structured connection configuration (host, port, database, bucket, etc.).")
    secret_payload: Optional[dict[str, Any]] = Field(None, description="Optional secret credentials (username, password, access_key, etc.). Never returned in responses.")


class UpdateConnectorRequest(BaseModel):
    """Schema for updating connector configuration or secret payload."""

    name: Optional[str] = Field(None, description="Updated connector name.")
    configuration: Optional[dict[str, Any]] = Field(None, description="Updated configuration parameters.")
    secret_payload: Optional[dict[str, Any]] = Field(None, description="Updated secret payload. Never returned in responses.")


class ConnectorResponse(BaseModel):
    """Schema representing a platform data connector definition without exposing secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    connector_type: str
    category: str
    configuration: dict[str, Any]
    credential_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ConnectorListResponse(BaseModel):
    """List response schema for platform data connectors."""

    items: list[ConnectorResponse]
    total: int


class ConnectorTestResponse(BaseModel):
    """Schema for connector connection test results."""

    connector_id: str
    name: str
    status: str
    capabilities: dict[str, Any]
