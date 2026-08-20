import pytest
from app.runtime.config import RuntimeConfig
from app.runtime.enums import RuntimeStatus, RuntimeType


def test_runtime_type_enum():
    """Test RuntimeType values."""
    assert RuntimeType.PYTHON.value == "python"
    assert RuntimeType.SQL.value == "sql"
    assert RuntimeType("python") == RuntimeType.PYTHON
    assert RuntimeType("sql") == RuntimeType.SQL


def test_runtime_status_enum():
    """Test RuntimeStatus values."""
    assert RuntimeStatus.STARTING.value == "starting"
    assert RuntimeStatus.RUNNING.value == "running"
    assert RuntimeStatus.TERMINATING.value == "terminating"
    assert RuntimeStatus.TERMINATED.value == "terminated"
    assert RuntimeStatus.FAILED.value == "failed"


def test_runtime_config_defaults():
    """Test RuntimeConfig default values and custom overrides."""
    default_cfg = RuntimeConfig()
    assert default_cfg.timeout_seconds == 600
    assert default_cfg.max_memory_mb == 2048
    assert default_cfg.env_vars == {}

    custom_cfg = RuntimeConfig(
        timeout_seconds=300,
        max_memory_mb=4096,
        env_vars={"PYTHONPATH": "/opt/app"},
    )
    assert custom_cfg.timeout_seconds == 300
    assert custom_cfg.max_memory_mb == 4096
    assert custom_cfg.env_vars["PYTHONPATH"] == "/opt/app"
