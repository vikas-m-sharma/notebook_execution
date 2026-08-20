import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.credentials.manager import CredentialManager
from app.connectors.enums import ConnectorCategory, ConnectorStatus, ConnectorType
from app.connectors.exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorError,
    ConnectorNotFoundError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.registry import ConnectorRegistry
from app.models.connector import Connector
from app.output.enums import OutputType
from app.output.manager import OutputManager
from app.repositories.connector import ConnectorRepository, CredentialRepository


class ConnectorManager:
    """Manager orchestrating data connector lifecycle, credential resolution, connection testing, and output logging."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conn_repo = ConnectorRepository(db)
        self.cred_repo = CredentialRepository(db)
        self.cred_manager = CredentialManager(self.cred_repo)
        self.output_manager = OutputManager()

    async def create_connector(
        self,
        name: str,
        connector_type: str,
        category: str,
        configuration: dict[str, Any],
        secret_payload: Optional[dict[str, Any]] = None,
    ) -> Connector:
        """Validate and create a new platform data connector definition with optional credentials."""
        # 1. Resolve and validate connector class from registry
        connector_cls = ConnectorRegistry.get(connector_type)

        # 2. Test instantiation and validation of configuration
        dummy_id = str(uuid.uuid4())
        temp_instance = connector_cls(
            connector_id=dummy_id,
            name=name,
            config=configuration,
            credentials=secret_payload,
        )
        temp_instance.validate_config()

        # 3. Store secret credentials if provided
        credential_id = None
        if secret_payload:
            cred = await self.cred_manager.create_credential(
                credential_type=connector_type,
                secret_payload=secret_payload,
            )
            credential_id = cred.credential_id

        # 4. Persist Connector record
        return await self.conn_repo.create(
            name=name,
            connector_type=connector_type.lower(),
            category=category.upper(),
            configuration=configuration,
            credential_id=credential_id,
            status=ConnectorStatus.CREATED.value,
        )

    async def get_connector(self, connector_id: uuid.UUID) -> Connector:
        """Get connector record by UUID."""
        conn = await self.conn_repo.get_by_id(connector_id)
        if not conn:
            raise ConnectorNotFoundError(str(connector_id))
        return conn

    async def list_connectors(self) -> list[Connector]:
        """List all platform connectors."""
        return list(await self.conn_repo.list_all())

    async def update_connector(
        self,
        connector_id: uuid.UUID,
        name: Optional[str] = None,
        configuration: Optional[dict[str, Any]] = None,
        secret_payload: Optional[dict[str, Any]] = None,
    ) -> Connector:
        """Update connector configuration or credentials."""
        conn = await self.get_connector(connector_id)

        updated_cred_id = conn.credential_id
        if secret_payload:
            if conn.credential_id:
                cred = await self.cred_manager.create_credential(
                    credential_type=conn.connector_type,
                    secret_payload=secret_payload,
                    credential_id=conn.credential_id,
                )
                updated_cred_id = cred.credential_id
            else:
                cred = await self.cred_manager.create_credential(
                    credential_type=conn.connector_type,
                    secret_payload=secret_payload,
                )
                updated_cred_id = cred.credential_id

        updated = await self.conn_repo.update(
            connector_id=connector_id,
            name=name,
            configuration=configuration,
            credential_id=updated_cred_id,
            status=ConnectorStatus.CREATED.value,
        )
        return updated  # type: ignore

    async def delete_connector(self, connector_id: uuid.UUID) -> bool:
        """Delete connector definition and its associated credentials."""
        conn = await self.get_connector(connector_id)
        if conn.credential_id:
            await self.cred_repo.delete(conn.credential_id)
        return await self.conn_repo.delete(connector_id)

    async def test_connector(self, connector_id: uuid.UUID) -> dict[str, Any]:
        """Test connection to target data source, update status, and log sanitized output."""
        conn = await self.get_connector(connector_id)

        # Update status to VALIDATING
        await self.conn_repo.update_status(connector_id, ConnectorStatus.VALIDATING.value)

        # Resolve credentials if credential_id exists
        resolved_creds = {}
        if conn.credential_id:
            resolved_creds = await self.cred_manager.resolve_credential(conn.credential_id) or {}

        try:
            instance = ConnectorFactory.create_connector(
                connector_id=str(conn.id),
                name=conn.name,
                connector_type=conn.connector_type,
                config=conn.configuration,
                credentials=resolved_creds,
            )

            is_ok = await instance.test_connection()
            status_val = ConnectorStatus.AVAILABLE.value if is_ok else ConnectorStatus.UNAVAILABLE.value

            await self.conn_repo.update_status(connector_id, status_val)

            # Log sanitized test result event to Phase 8 OutputManager
            events, _ = self.output_manager.create_output_events(
                execution_id=f"conn-test-{conn.id}",
                session_id="connector-manager",
                notebook_id=None,
                stdout=f"Connector '{conn.name}' ({conn.connector_type}) connection test: {status_val}\n",
                status="ok",
            )
            await self.output_manager.process_and_persist_events(self.db, events)

            return {
                "connector_id": str(conn.id),
                "name": conn.name,
                "status": status_val,
                "capabilities": instance.capabilities().__dict__,
            }

        except Exception as exc:
            await self.conn_repo.update_status(connector_id, ConnectorStatus.ERROR.value)

            # Log sanitized error event
            events, _ = self.output_manager.create_output_events(
                execution_id=f"conn-test-{conn.id}",
                session_id="connector-manager",
                notebook_id=None,
                stderr=f"Connector '{conn.name}' connection test failed: {exc}\n",
                status="failed",
            )
            await self.output_manager.process_and_persist_events(self.db, events)

            raise ConnectorConnectionError(str(conn.id), str(exc)) from exc
