from typing import Type

from app.connectors.base.connector import BaseConnector
from app.connectors.enums import ConnectorType
from app.connectors.exceptions import ConnectorNotFoundError
from app.connectors.nosql.mongodb import MongoDBConnector
from app.connectors.object_storage.s3 import AWSS3Connector
from app.connectors.relational.mssql import MSSQLConnector
from app.connectors.relational.mysql import MySQLConnector
from app.connectors.relational.postgresql import PostgreSQLConnector


class ConnectorRegistry:
    """Registry maintaining available connector type implementations."""

    _registry: dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_type: str, connector_cls: Type[BaseConnector]) -> None:
        """Register a concrete connector implementation class for a type identifier."""
        canonical_type = connector_type.strip().lower()
        cls._registry[canonical_type] = connector_cls

    @classmethod
    def get(cls, connector_type: str) -> Type[BaseConnector]:
        """Resolve a concrete connector class by type identifier."""
        canonical_type = connector_type.strip().lower()
        if canonical_type not in cls._registry:
            raise ConnectorNotFoundError(connector_type)
        return cls._registry[canonical_type]

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered connector type identifiers."""
        return sorted(list(cls._registry.keys()))


# Register V1 Connectors
ConnectorRegistry.register(ConnectorType.POSTGRESQL.value, PostgreSQLConnector)
ConnectorRegistry.register(ConnectorType.MYSQL.value, MySQLConnector)
ConnectorRegistry.register(ConnectorType.MSSQL.value, MSSQLConnector)
ConnectorRegistry.register(ConnectorType.MONGODB.value, MongoDBConnector)
ConnectorRegistry.register(ConnectorType.S3.value, AWSS3Connector)
