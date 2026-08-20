from enum import Enum


class DependencyStatus(str, Enum):
    """Lifecycle states for dependency installation operations."""

    REQUESTED = "REQUESTED"
    VALIDATING = "VALIDATING"
    RESOLVING = "RESOLVING"
    INSTALLING = "INSTALLING"
    VERIFYING = "VERIFYING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
