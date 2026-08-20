from abc import ABC, abstractmethod
from typing import Any, Optional

from app.connectors.base.connector import BaseConnector, ConnectorCapabilities
from app.connectors.enums import ConnectorCategory, ConnectorType
from app.connectors.exceptions import ConnectorConfigurationError


class BaseRelationalConnector(BaseConnector, ABC):
    """Abstract base connector for relational SQL database systems."""

    def __init__(
        self,
        connector_id: str,
        name: str,
        connector_type: ConnectorType,
        config: dict[str, Any],
        credentials: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            connector_id=connector_id,
            name=name,
            connector_type=connector_type,
            category=ConnectorCategory.RELATIONAL_DATABASE,
            config=config,
            credentials=credentials,
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_read=True,
            can_write=True,
            supports_transactions=True,
            supports_query=True,
            supports_object_storage=False,
        )

    def validate_config(self) -> None:
        """Validate standard relational connection config parameters (host, port, database)."""
        required_fields = ["host", "port", "database"]
        for field_name in required_fields:
            if field_name not in self.config or self.config[field_name] is None:
                raise ConnectorConfigurationError(
                    self.connector_type.value, f"Missing required configuration field '{field_name}'."
                )

    @abstractmethod
    async def query(self, query_str: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Execute parameterized SQL query and return list of row dictionaries."""
        pass
