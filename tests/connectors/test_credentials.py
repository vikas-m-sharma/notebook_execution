import pytest

from app.connectors.credentials.manager import CredentialManager
from app.repositories.connector import CredentialRepository


@pytest.mark.asyncio
async def test_credential_manager_creation_and_sanitization(db_session):
    """Test storing secret credentials and verifying sanitization masks sensitive keys."""
    repo = CredentialRepository(db_session)
    manager = CredentialManager(repo)

    raw_secret = {
        "username": "db_user",
        "password": "super_secret_password_123",
        "aws_secret_access_key": "xyz987secret",
    }

    # Create credential
    cred = await manager.create_credential(
        credential_type="postgresql",
        secret_payload=raw_secret,
    )
    assert cred.credential_id.startswith("cred-")

    # Resolve raw credential internally
    resolved = await manager.resolve_credential(cred.credential_id)
    assert resolved["password"] == "super_secret_password_123"

    # Sanitize payload for public exposure
    sanitized = CredentialManager.sanitize_credential_payload(resolved)
    assert sanitized["username"] == "db_user"
    assert sanitized["password"] == "********"
    assert sanitized["aws_secret_access_key"] == "********"
