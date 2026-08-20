import os
import uuid
from datetime import datetime, timezone
import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.encryption import decrypt_payload, encrypt_payload
from app.core.security import verify_api_key
from app.jobs.schedule_utils import calculate_next_run, validate_cron_expression
from app.main import app
from app.runtime.python_worker import _sanitize_worker_environment
from app.schemas.notebook_cell import NotebookCellCreate
from app.schemas.dependency import DependencyCreate, DependencyInstallRequest
from app.connectors.credentials.manager import CredentialManager
from app.repositories.connector import CredentialRepository


@pytest.mark.asyncio
async def test_authentication_enforcement(db_session, monkeypatch):
    """SEC-001: Test API Key authentication when REQUIRE_AUTH=True."""
    test_key = "test-secret-api-key-12345"
    test_settings = Settings(
        REQUIRE_AUTH=True,
        API_KEY=test_key,
        ENVIRONMENT="testing",
    )
    monkeypatch.setattr("app.core.security.get_settings", lambda: test_settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Request without header -> 401
        res_no_auth = await client.get("/api/v1/workspaces")
        assert res_no_auth.status_code == 401
        assert "Invalid or missing API key" in res_no_auth.json()["detail"]

        # Request with wrong header -> 401
        res_wrong_auth = await client.get(
            "/api/v1/workspaces",
            headers={"X-API-Key": "wrong-key"},
        )
        assert res_wrong_auth.status_code == 401

        # Health probe endpoints MUST remain unauthenticated
        res_health_root = await client.get("/health")
        assert res_health_root.status_code == 200

        res_health_v1 = await client.get("/api/v1/health")
        assert res_health_v1.status_code == 200


@pytest.mark.asyncio
async def test_credential_encryption_and_decryption(db_session, monkeypatch):
    """SEC-002: Test Fernet symmetric encryption of credentials at rest."""
    key = Fernet.generate_key().decode()
    test_settings = Settings(CREDENTIAL_ENCRYPTION_KEY=key, ENVIRONMENT="testing")
    monkeypatch.setattr("app.core.encryption.get_settings", lambda: test_settings)

    raw_payload = {"username": "admin", "password": "supersecretpassword", "port": 5432}
    encrypted = encrypt_payload(raw_payload)

    # Must be encrypted envelope
    assert encrypted["_enc"] is True
    assert isinstance(encrypted["_data"], str)
    assert "supersecretpassword" not in encrypted["_data"]

    # Decrypt with correct key
    decrypted = decrypt_payload(encrypted)
    assert decrypted["password"] == "supersecretpassword"
    assert decrypted["username"] == "admin"

    # Full repository roundtrip
    repo = CredentialRepository(db_session)
    manager = CredentialManager(repo)

    cred = await manager.create_credential(
        credential_type="postgresql",
        secret_payload=raw_payload,
    )
    resolved = await manager.resolve_credential(cred.credential_id)
    assert resolved["password"] == "supersecretpassword"


def test_worker_environment_variable_sanitization(monkeypatch):
    """SEC-003: Test that host secrets and DATABASE_URL are purged from worker environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:secret@db:5432/prod")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "super-secret-master-key")
    monkeypatch.setenv("CUSTOM_API_SECRET", "jwt_secret_token_xyz")
    monkeypatch.setenv("PATH", "C:\\Windows\\System32;C:\\Python")

    assert "DATABASE_URL" in os.environ
    assert "CREDENTIAL_ENCRYPTION_KEY" in os.environ

    _sanitize_worker_environment()

    assert "DATABASE_URL" not in os.environ
    assert "CREDENTIAL_ENCRYPTION_KEY" not in os.environ
    assert "CUSTOM_API_SECRET" not in os.environ
    assert "PATH" in os.environ


def test_cron_5_field_schedule_evaluation():
    """SEC-008: Verify correct 5-field cron calculation using croniter."""
    base_t = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Daily at 2:00 AM (0 2 * * *)
    next_daily = calculate_next_run("0 2 * * *", "UTC", base_time=base_t)
    assert next_daily == datetime(2026, 8, 21, 2, 0, 0, tzinfo=timezone.utc)

    # 2. Hourly (0 * * * *)
    next_hourly = calculate_next_run("0 * * * *", "UTC", base_time=base_t)
    assert next_hourly == datetime(2026, 8, 20, 11, 0, 0, tzinfo=timezone.utc)

    # 3. Every 15 minutes (*/15 * * * *)
    next_15m = calculate_next_run("*/15 * * * *", "UTC", base_time=base_t)
    assert next_15m == datetime(2026, 8, 20, 10, 15, 0, tzinfo=timezone.utc)


def test_input_validation_bounds():
    """SEC-011 / SEC-015 / SEC-016: Test schema bounds on source, timeouts, and package names."""
    # Valid source under 1MB passes
    cell = NotebookCellCreate(position=0, cell_type="code", source="x = 1")
    assert cell.source == "x = 1"

    # Source exceeding 1MB raises ValidationError
    with pytest.raises(ValidationError):
        NotebookCellCreate(position=0, cell_type="code", source="x" * 1_000_001)

    # Valid dependency timeout
    dep_req = DependencyInstallRequest(timeout_seconds=300.0)
    assert dep_req.timeout_seconds == 300.0

    # Negative timeout raises ValidationError
    with pytest.raises(ValidationError):
        DependencyInstallRequest(timeout_seconds=-1.0)

    # Timeout exceeding 600s raises ValidationError
    with pytest.raises(ValidationError):
        DependencyInstallRequest(timeout_seconds=601.0)
