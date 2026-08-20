from typing import Any

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    """Configuration options for initializing an execution runtime."""

    timeout_seconds: int = Field(600, ge=1, json_schema_extra={"example": 600})
    max_memory_mb: int = Field(2048, ge=128, json_schema_extra={"example": 2048})
    env_vars: dict[str, str] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
