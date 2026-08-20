from enum import Enum


class ConnectorType(str, Enum):
    """Supported platform data connector types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MSSQL = "mssql"
    MONGODB = "mongodb"
    S3 = "s3"


class ConnectorCategory(str, Enum):
    """General categorizations for connectors."""

    RELATIONAL_DATABASE = "RELATIONAL_DATABASE"
    NOSQL_DATABASE = "NOSQL_DATABASE"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    DATA_WAREHOUSE = "DATA_WAREHOUSE"
    API = "API"
    FILE = "FILE"
    STREAMING = "STREAMING"


class ConnectorStatus(str, Enum):
    """Lifecycle states for data connectors."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    DISABLED = "DISABLED"
