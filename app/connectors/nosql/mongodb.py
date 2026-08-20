from typing import Any, Optional

from app.connectors.base.connector import BaseConnector, ConnectorCapabilities
from app.connectors.enums import ConnectorCategory, ConnectorType
from app.connectors.exceptions import ConnectorConfigurationError, ConnectorOperationError


class MongoDBConnector(BaseConnector):
    """MongoDB NoSQL database connector implementation."""

    def __init__(
        self,
        connector_id: str,
        name: str,
        config: dict[str, Any],
        credentials: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            connector_id=connector_id,
            name=name,
            connector_type=ConnectorType.MONGODB,
            category=ConnectorCategory.NOSQL_DATABASE,
            config=config,
            credentials=credentials,
        )
        self.host = str(self.config.get("host", "localhost"))
        self.port = int(self.config.get("port", 27017))
        self.database = str(self.config.get("database", "admin"))

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_read=True,
            can_write=True,
            supports_transactions=False,
            supports_query=True,
            supports_object_storage=False,
        )

    def validate_config(self) -> None:
        required_fields = ["host", "port", "database"]
        for field_name in required_fields:
            if field_name not in self.config or self.config[field_name] is None:
                raise ConnectorConfigurationError(
                    self.connector_type.value, f"Missing required configuration field '{field_name}'."
                )

    async def test_connection(self) -> bool:
        self.validate_config()
        return True

    async def connect(self) -> None:
        self.validate_config()
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def query(self, query_str: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        if not self.is_connected:
            await self.connect()

        # Document collection query simulation
        return [{"status": "success", "database": self.database, "collection_query": query_str}]
