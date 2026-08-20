class DependencyError(Exception):
    """Base exception for all dependency management errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DependencyValidationError(DependencyError):
    """Raised when a package name or version specifier fails syntax/security validation."""

    def __init__(self, package_name: str, reason: str) -> None:
        super().__init__(f"Invalid dependency configuration for '{package_name}': {reason}")
        self.package_name = package_name
        self.reason = reason


class DependencyResolutionError(DependencyError):
    """Raised when dependency package version resolution or requirement constraints conflict."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Dependency resolution error: {message}")


class DependencyInstallationError(DependencyError):
    """Raised when pip installation fails inside the isolated runtime."""

    def __init__(self, operation_id: str, details: str) -> None:
        super().__init__(f"Dependency installation failed for operation '{operation_id}': {details}")
        self.operation_id = operation_id
        self.details = details


class DependencyTimeoutError(DependencyError):
    """Raised when package installation exceeds the configured timeout."""

    def __init__(self, operation_id: str, timeout_seconds: float) -> None:
        super().__init__(f"Dependency installation timed out for operation '{operation_id}' after {timeout_seconds}s.")
        self.operation_id = operation_id
        self.timeout_seconds = timeout_seconds
