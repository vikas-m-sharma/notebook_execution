from typing import Any, Optional

from app.connectors.base.connector import BaseConnector
from app.connectors.registry import ConnectorRegistry


class ConnectorFactory:
    """Factory creating concrete BaseConnector instances from configuration and credentials."""

    @classmethod
    def create_connector(
        self,
        connector_id: str,
        name: str,
        connector_type: str,
        config: dict[str, Any],
        credentials: Optional[dict[str, Any]] = None,
    ) -> BaseConnector:
        """Instantiate concrete connector using registered class."""
        connector_cls = ConnectorRegistry.get(connector_type)
        connector_inst = connector_cls(
            connector_id=connector_id,
            name=name,
            config=config,
            credentials=credentials,
        )
        connector_inst.validate_config()
        return connector_inst
