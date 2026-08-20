import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorNotFoundError,
)
from app.connectors.manager import ConnectorManager
from app.core.database import get_db
from app.schemas.connector import (
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorTestResponse,
    CreateConnectorRequest,
    UpdateConnectorRequest,
)

router = APIRouter()


@router.post(
    "/connectors",
    response_model=ConnectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Data Connector",
    description="Create a new platform data connector definition with optional secret credentials.",
)
async def create_connector(
    data: CreateConnectorRequest,
    db: AsyncSession = Depends(get_db),
) -> ConnectorResponse:
    manager = ConnectorManager(db)
    try:
        conn = await manager.create_connector(
            name=data.name,
            connector_type=data.connector_type,
            category=data.category,
            configuration=data.configuration,
            secret_payload=data.secret_payload,
        )
        await db.commit()
        return ConnectorResponse.model_validate(conn)
    except (ConnectorConfigurationError, ConnectorNotFoundError) as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/connectors",
    response_model=ConnectorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Data Connectors",
    description="List all platform data connectors without exposing secrets.",
)
async def list_connectors(
    db: AsyncSession = Depends(get_db),
) -> ConnectorListResponse:
    manager = ConnectorManager(db)
    connectors = await manager.list_connectors()
    items = [ConnectorResponse.model_validate(c) for c in connectors]
    return ConnectorListResponse(items=items, total=len(items))


@router.get(
    "/connectors/{connector_id}",
    response_model=ConnectorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Data Connector",
    description="Get connector details by UUID without exposing secrets.",
)
async def get_connector(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectorResponse:
    manager = ConnectorManager(db)
    try:
        conn = await manager.get_connector(connector_id)
        return ConnectorResponse.model_validate(conn)
    except ConnectorNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.patch(
    "/connectors/{connector_id}",
    response_model=ConnectorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Data Connector",
    description="Update data connector configuration or credentials.",
)
async def update_connector(
    connector_id: uuid.UUID,
    data: UpdateConnectorRequest,
    db: AsyncSession = Depends(get_db),
) -> ConnectorResponse:
    manager = ConnectorManager(db)
    try:
        updated = await manager.update_connector(
            connector_id=connector_id,
            name=data.name,
            configuration=data.configuration,
            secret_payload=data.secret_payload,
        )
        await db.commit()
        return ConnectorResponse.model_validate(updated)
    except ConnectorNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.delete(
    "/connectors/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Data Connector",
    description="Delete a platform data connector and its associated credential reference.",
)
async def delete_connector(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    manager = ConnectorManager(db)
    try:
        await manager.delete_connector(connector_id)
        await db.commit()
    except ConnectorNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/connectors/{connector_id}/test",
    response_model=ConnectorTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test Data Connector Connection",
    description="Test connection to target data source and return capability metadata.",
)
async def test_connector(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectorTestResponse:
    manager = ConnectorManager(db)
    try:
        res = await manager.test_connector(connector_id)
        await db.commit()
        return ConnectorTestResponse(
            connector_id=res["connector_id"],
            name=res["name"],
            status=res["status"],
            capabilities=res["capabilities"],
        )
    except ConnectorNotFoundError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ConnectorConnectionError as err:
        await db.commit()  # status updated to ERROR
        conn_rec = await manager.conn_repo.get_by_id(connector_id)
        return ConnectorTestResponse(
            connector_id=str(connector_id),
            name=conn_rec.name if conn_rec else "Unknown",
            status="ERROR",
            capabilities={},
        )
