import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector, Credential


class ConnectorRepository:
    """Async repository for managing Connector persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        connector_type: str,
        category: str,
        configuration: dict[str, Any],
        credential_id: Optional[str] = None,
        status: str = "CREATED",
    ) -> Connector:
        """Create a new Connector record."""
        connector = Connector(
            name=name,
            connector_type=connector_type,
            category=category,
            configuration=configuration,
            credential_id=credential_id,
            status=status,
        )
        self.session.add(connector)
        await self.session.flush()
        await self.session.refresh(connector)
        return connector

    async def get_by_id(self, connector_id: uuid.UUID) -> Optional[Connector]:
        """Retrieve a Connector record by primary key UUID."""
        stmt = select(Connector).where(Connector.id == connector_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Connector]:
        """Retrieve a Connector record by unique string name."""
        stmt = select(Connector).where(Connector.name == name)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self) -> Sequence[Connector]:
        """List all defined Connectors ordered by name."""
        stmt = select(Connector).order_by(Connector.name.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def update(
        self,
        connector_id: uuid.UUID,
        name: Optional[str] = None,
        configuration: Optional[dict[str, Any]] = None,
        credential_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Connector]:
        """Update Connector attributes."""
        conn_rec = await self.get_by_id(connector_id)
        if not conn_rec:
            return None
        if name is not None:
            conn_rec.name = name
        if configuration is not None:
            conn_rec.configuration = configuration
        if credential_id is not None:
            conn_rec.credential_id = credential_id
        if status is not None:
            conn_rec.status = status
        await self.session.flush()
        await self.session.refresh(conn_rec)
        return conn_rec

    async def update_status(self, connector_id: uuid.UUID, status: str) -> Optional[Connector]:
        """Update Connector status."""
        return await self.update(connector_id, status=status)

    async def delete(self, connector_id: uuid.UUID) -> bool:
        """Delete a Connector record by UUID."""
        conn_rec = await self.get_by_id(connector_id)
        if not conn_rec:
            return False
        await self.session.delete(conn_rec)
        await self.session.flush()
        return True


class CredentialRepository:
    """Async repository for managing Credential persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        credential_id: str,
        credential_type: str,
        payload: dict[str, Any],
    ) -> Credential:
        """Create a new Credential record."""
        cred = Credential(
            credential_id=credential_id,
            credential_type=credential_type,
            encrypted_payload=payload,
        )
        self.session.add(cred)
        await self.session.flush()
        await self.session.refresh(cred)
        return cred

    async def get_by_credential_id(self, credential_id: str) -> Optional[Credential]:
        """Retrieve a Credential record by unique string credential_id."""
        stmt = select(Credential).where(Credential.credential_id == credential_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def delete(self, credential_id: str) -> bool:
        """Delete a Credential record by unique string credential_id."""
        cred = await self.get_by_credential_id(credential_id)
        if not cred:
            return False
        await self.session.delete(cred)
        await self.session.flush()
        return True
