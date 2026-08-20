from enum import Enum


class OutputType(str, Enum):
    """Categorized types for notebook execution output events."""

    STDOUT = "stdout"
    STDERR = "stderr"
    RESULT = "result"
    TRACEBACK = "traceback"
    ERROR = "error"
    TEXT = "text"
