import pytest

from app.connectors.enums import ConnectorType
from app.connectors.exceptions import ConnectorNotFoundError
from app.connectors.registry import ConnectorRegistry


def test_connector_registry_v1_types():
    """Verify all V1 connector types are registered and resolvable in ConnectorRegistry."""
    registered = ConnectorRegistry.list_types()
    v1_types = ["postgresql", "mysql", "mssql", "mongodb", "s3"]

    for t in v1_types:
        assert t in registered
        cls = ConnectorRegistry.get(t)
        assert cls is not None


def test_connector_registry_unknown_type():
    """Verify requesting an unknown connector type raises ConnectorNotFoundError."""
    with pytest.raises(ConnectorNotFoundError):
        ConnectorRegistry.get("oracle_db_nonexistent")
