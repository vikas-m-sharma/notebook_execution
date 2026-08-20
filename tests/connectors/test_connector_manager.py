import pytest

from app.connectors.enums import ConnectorStatus
from app.connectors.manager import ConnectorManager
from app.repositories.output import ExecutionOutputRepository


@pytest.mark.asyncio
async def test_connector_manager_crud_and_test_connection(db_session):
    """Test ConnectorManager creation, update, listing, test connection, and log output generation."""
    manager = ConnectorManager(db_session)

    # 1. Create connector
    conn = await manager.create_connector(
        name="sales-analytics-db",
        connector_type="postgresql",
        category="RELATIONAL_DATABASE",
        configuration={"host": "localhost", "port": 5432, "database": "sales"},
        secret_payload={"username": "sales_admin", "password": "super_secret_password"},
    )
    assert conn.name == "sales-analytics-db"
    assert conn.credential_id is not None
    assert conn.status == ConnectorStatus.CREATED.value

    # 2. List connectors
    all_conns = await manager.list_connectors()
    assert len(all_conns) == 1

    # 3. Test connector connection
    test_res = await manager.test_connector(conn.id)
    assert test_res["status"] == ConnectorStatus.AVAILABLE.value
    assert test_res["capabilities"]["can_read"] is True

    # 4. Verify Phase 8 output log event was generated (sanitized)
    output_repo = ExecutionOutputRepository(db_session)
    logs = await output_repo.list_by_execution_id(f"conn-test-{conn.id}")
    assert len(logs) == 1
    assert "super_secret_password" not in logs[0].content
    assert "connection test: AVAILABLE" in logs[0].content

    # 5. Delete connector
    deleted = await manager.delete_connector(conn.id)
    assert deleted is True
