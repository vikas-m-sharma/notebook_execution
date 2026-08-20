class ConnectorError(Exception):
    """Base exception for all platform data connector errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConnectorNotFoundError(ConnectorError):
    """Raised when a requested connector ID or connector type does not exist."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Connector '{identifier}' not found.")
        self.identifier = identifier


class ConnectorConfigurationError(ConnectorError):
    """Raised when connector configuration parameters are invalid or missing."""

    def __init__(self, connector_type: str, details: str) -> None:
        super().__init__(f"Invalid configuration for connector '{connector_type}': {details}")
        self.connector_type = connector_type
        self.details = details


class ConnectorAuthenticationError(ConnectorError):
    """Raised when authentication against the target data source fails."""

    def __init__(self, connector_id: str, details: str) -> None:
        super().__init__(f"Authentication failed for connector '{connector_id}': {details}")
        self.connector_id = connector_id
        self.details = details


class ConnectorConnectionError(ConnectorError):
    """Raised when network or database connectivity to the data source fails."""

    def __init__(self, connector_id: str, details: str) -> None:
        super().__init__(f"Connection failed for connector '{connector_id}': {details}")
        self.connector_id = connector_id
        self.details = details


class ConnectorTimeoutError(ConnectorError):
    """Raised when a connector operation exceeds the timeout limit."""

    def __init__(self, connector_id: str, timeout_seconds: float) -> None:
        super().__init__(f"Connector '{connector_id}' operation timed out after {timeout_seconds}s.")
        self.connector_id = connector_id
        self.timeout_seconds = timeout_seconds


class ConnectorOperationError(ConnectorError):
    """Raised when a query, read, or write operation fails on the external data source."""

    def __init__(self, connector_id: str, details: str) -> None:
        super().__init__(f"Operation failed on connector '{connector_id}': {details}")
        self.connector_id = connector_id
        self.details = details
