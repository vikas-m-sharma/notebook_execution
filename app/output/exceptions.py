class OutputError(Exception):
    """Base exception for Output / Logs domain errors."""

    pass


class OutputLimitExceededError(OutputError):
    """Raised when output content exceeds maximum permitted size limit."""

    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(
            f"Output size ({size} bytes) exceeds maximum limit ({limit} bytes)."
        )
