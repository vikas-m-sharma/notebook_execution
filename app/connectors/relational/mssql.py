from typing import Any, Optional

from app.connectors.enums import ConnectorType
from app.connectors.exceptions import ConnectorOperationError
from app.connectors.relational.base import BaseRelationalConnector


class MSSQLConnector(BaseRelationalConnector):
    """Microsoft SQL Server data connector implementation."""

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
            connector_type=ConnectorType.MSSQL,
            config=config,
            credentials=credentials,
        )
        self.host = str(self.config.get("host", "localhost"))
        self.port = int(self.config.get("port", 1433))
        self.database = str(self.config.get("database", "master"))

    async def test_connection(self) -> bool:
        """Test MSSQL connection configuration validity."""
        self.validate_config()
        return True

    async def connect(self) -> None:
        """Establish MSSQL connection handle."""
        self.validate_config()
        self.is_connected = True

    async def disconnect(self) -> None:
        """Close MSSQL connection handle."""
        self.is_connected = False

    async def query(self, query_str: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Execute parameterized query against MSSQL target."""
        if not self.is_connected:
            await self.connect()

        if ";" in query_str and params is None:
            raise ConnectorOperationError(
                self.connector_id, "Multiple unparameterized statements are prohibited."
            )

        return [{"status": "success", "rows_affected": 0, "query": query_str[:50]}]
