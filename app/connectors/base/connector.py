from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.connectors.enums import ConnectorCategory, ConnectorType


@dataclass
class ConnectorCapabilities:
    """Dataclass advertising supported capabilities of a connector."""

    can_read: bool = True
    can_write: bool = False
    supports_transactions: bool = False
    supports_query: bool = False
    supports_object_storage: bool = False
    extra_capabilities: dict[str, bool] = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base class for all platform data connectors."""

    def __init__(
        self,
        connector_id: str,
        name: str,
        connector_type: ConnectorType,
        category: ConnectorCategory,
        config: dict[str, Any],
        credentials: Optional[dict[str, Any]] = None,
    ) -> None:
        self.connector_id = connector_id
        self.name = name
        self.connector_type = connector_type
        self.category = category
        self.config = config
        self._credentials = credentials or {}
        self.is_connected = False

    @classmethod
    @abstractmethod
    def capabilities(cls) -> ConnectorCapabilities:
        """Return capabilities supported by this connector implementation."""
        pass

    @abstractmethod
    def validate_config(self) -> None:
        """Validate required configuration parameters. Raise ConnectorConfigurationError if invalid."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to external target data source without opening a permanent handle."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection or client handle to the external data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Safely close and release connection resources."""
        pass

    async def query(self, query_str: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Execute a query if supported by this connector."""
        raise NotImplementedError(f"Query operation is not supported by connector '{self.name}'.")

    async def read_object(self, object_key: str) -> bytes:
        """Read binary object content if supported by object storage connector."""
        raise NotImplementedError(f"Read object operation is not supported by connector '{self.name}'.")

    async def write_object(self, object_key: str, data: bytes) -> bool:
        """Write binary object content if supported by object storage connector."""
        raise NotImplementedError(f"Write object operation is not supported by connector '{self.name}'.")

    def sanitize_metadata(self) -> dict[str, Any]:
        """Return safe, sanitized metadata representation without sensitive credentials."""
        sanitized_config = {
            k: v for k, v in self.config.items() if "password" not in k.lower() and "secret" not in k.lower() and "token" not in k.lower()
        }
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "connector_type": self.connector_type.value,
            "category": self.category.value,
            "configuration": sanitized_config,
            "capabilities": self.capabilities().__dict__,
        }
