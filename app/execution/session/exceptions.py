import uuid


class SessionError(Exception):
    """Base exception for Execution Session domain errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a requested session is not found in registry."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Execution session '{session_id}' not found.")


class SessionNotActiveError(SessionError):
    """Raised when attempting to execute code in a non-active session."""

    def __init__(self, session_id: str, current_status: str) -> None:
        self.session_id = session_id
        self.current_status = current_status
        super().__init__(
            f"Execution session '{session_id}' is not active (current status: '{current_status}')."
        )


class SessionExecutionError(SessionError):
    """Raised when a session execution fails due to underlying worker/runtime failure."""

    def __init__(self, session_id: str, reason: str) -> None:
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Execution in session '{session_id}' failed: {reason}")
