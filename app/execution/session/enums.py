from enum import Enum


class SessionStatus(str, Enum):
    """Lifecycle status states of an Execution Session."""

    CREATED = "created"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
