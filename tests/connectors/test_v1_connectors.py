import pytest

from app.connectors.exceptions import ConnectorConfigurationError, ConnectorOperationError
from app.connectors.nosql.mongodb import MongoDBConnector
from app.connectors.object_storage.s3 import AWSS3Connector
from app.connectors.relational.mssql import MSSQLConnector
from app.connectors.relational.mysql import MySQLConnector
from app.connectors.relational.postgresql import PostgreSQLConnector


@pytest.mark.asyncio
async def test_v1_relational_connectors_lifecycle_and_parameterized_queries():
    """Test PostgreSQL, MySQL, and MSSQL connector instantiation, configuration validation, and queries."""
    pg_config = {"host": "localhost", "port": 5432, "database": "testdb"}
    pg = PostgreSQLConnector("c-pg", "PG DB", pg_config, {"password": "secret"})
    assert pg.capabilities().can_read is True
    assert pg.capabilities().supports_query is True

    await pg.connect()
    assert pg.is_connected is True

    # Parameterized query execution
    res = await pg.query("SELECT * FROM users WHERE id = :id", {"id": 10})
    assert len(res) == 1

    # Unparameterized query with semicolon protection
    with pytest.raises(ConnectorOperationError):
        await pg.query("SELECT 1; DROP TABLE users;")

    await pg.disconnect()
    assert pg.is_connected is False

    # MySQL
    mysql_config = {"host": "localhost", "port": 3306, "database": "mydb"}
    mysql = MySQLConnector("c-mysql", "MySQL DB", mysql_config)
    assert await mysql.test_connection() is True

    # MSSQL
    mssql_config = {"host": "localhost", "port": 1433, "database": "master"}
    mssql = MSSQLConnector("c-mssql", "MSSQL DB", mssql_config)
    assert await mssql.test_connection() is True


@pytest.mark.asyncio
async def test_v1_mongodb_and_s3_connectors():
    """Test MongoDB and AWS S3 connector capabilities and operations."""
    # MongoDB
    mongo_config = {"host": "localhost", "port": 27017, "database": "analytics"}
    mongo = MongoDBConnector("c-mongo", "Mongo", mongo_config)
    assert mongo.capabilities().supports_object_storage is False
    assert await mongo.test_connection() is True

    # S3 Object Storage
    s3_config = {"bucket": "my-analytics-bucket", "region": "us-east-1"}
    s3 = AWSS3Connector("c-s3", "S3 Bucket", s3_config)
    assert s3.capabilities().supports_object_storage is True

    await s3.connect()
    w_ok = await s3.write_object("data/report.csv", b"col1,col2\n1,2")
    assert w_ok is True

    read_bytes = await s3.read_object("data/report.csv")
    assert read_bytes == b"col1,col2\n1,2"
    await s3.disconnect()
