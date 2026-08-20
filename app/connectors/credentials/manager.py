import uuid
from typing import Any, Optional

from app.core.encryption import decrypt_payload
from app.models.connector import Credential
from app.repositories.connector import CredentialRepository


class CredentialManager:
    """Manager for securely creating, resolving, and sanitizing connector credentials."""

    def __init__(self, repo: CredentialRepository) -> None:
        self.repo = repo

    async def create_credential(
        self,
        credential_type: str,
        secret_payload: dict[str, Any],
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Store credential payload under a secure credential_id reference."""
        cid = credential_id or f"cred-{uuid.uuid4()}"
        return await self.repo.create(
            credential_id=cid,
            credential_type=credential_type,
            payload=secret_payload,
        )

    async def resolve_credential(self, credential_id: str) -> Optional[dict[str, Any]]:
        """Resolve actual raw credential payload for a valid credential_id reference."""
        cred = await self.repo.get_by_credential_id(credential_id)
        if not cred:
            return None
        return decrypt_payload(cred.encrypted_payload)

    @classmethod
    def sanitize_credential_payload(cls, payload: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Return a sanitized copy of a credential payload with sensitive fields masked."""
        if not payload:
            return {}

        sanitized: dict[str, Any] = {}
        for k, v in payload.items():
            k_lower = k.lower()
            if any(term in k_lower for term in ["password", "secret", "token", "private_key", "key"]):
                sanitized[k] = "********"
            else:
                sanitized[k] = v
        return sanitized
