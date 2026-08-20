from typing import Any, Optional

from app.connectors.base.connector import BaseConnector, ConnectorCapabilities
from app.connectors.enums import ConnectorCategory, ConnectorType
from app.connectors.exceptions import ConnectorConfigurationError, ConnectorOperationError


class AWSS3Connector(BaseConnector):
    """AWS S3 object storage connector implementation."""

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
            connector_type=ConnectorType.S3,
            category=ConnectorCategory.OBJECT_STORAGE,
            config=config,
            credentials=credentials,
        )
        self.bucket = str(self.config.get("bucket", ""))
        self.region = str(self.config.get("region", "us-east-1"))
        self._object_cache: dict[str, bytes] = {}

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_read=True,
            can_write=True,
            supports_transactions=False,
            supports_query=False,
            supports_object_storage=True,
        )

    def validate_config(self) -> None:
        required_fields = ["bucket", "region"]
        for field_name in required_fields:
            if field_name not in self.config or not self.config[field_name]:
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

    async def read_object(self, object_key: str) -> bytes:
        if not self.is_connected:
            await self.connect()

        if object_key in self._object_cache:
            return self._object_cache[object_key]

        return f"S3 object data for s3://{self.bucket}/{object_key}".encode("utf-8")

    async def write_object(self, object_key: str, data: bytes) -> bool:
        if not self.is_connected:
            await self.connect()

        self._object_cache[object_key] = data
        return True
