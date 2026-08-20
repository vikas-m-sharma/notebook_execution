"""
app/core/encryption.py

SEC-002: Symmetric encryption utilities for credential payloads at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.

Key management:
- The encryption key is loaded from settings.CREDENTIAL_ENCRYPTION_KEY.
- The key must be a valid URL-safe base64-encoded 32-byte value.
  Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
- If the key is not set (empty string), credentials are stored as plaintext JSON
  with a CRITICAL log warning. This is only acceptable in development environments.
- Applications must NEVER log decrypted payload values.

Encryption format:
- Plaintext: JSON-serialized bytes of the credential dict
- Ciphertext: Fernet token (base64url encoded, includes IV + HMAC)
- Database column: stores the ciphertext string as the JSON string value
"""
import json
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Sentinel value stored in DB when encryption is not configured
_PLAINTEXT_PREFIX = "plaintext:"


def _get_fernet():
    """Lazily import and return a Fernet instance using the configured key."""
    from cryptography.fernet import Fernet, InvalidToken  # noqa: F401 — re-exported for callers

    settings = get_settings()
    key = settings.CREDENTIAL_ENCRYPTION_KEY.strip()
    if not key:
        return None
    return Fernet(key.encode())


def encrypt_payload(payload: dict) -> dict:
    """
    SEC-002: Encrypt a credential payload dict before database persistence.

    Returns a dict with a single key "ciphertext" containing the encrypted value,
    OR the original payload prefixed with "plaintext:" if no key is configured.
    """
    fernet = _get_fernet()
    if fernet is None:
        logger.critical(
            "SEC-002: CREDENTIAL_ENCRYPTION_KEY is not set. "
            "Credential payload is being stored as PLAINTEXT. "
            "Set CREDENTIAL_ENCRYPTION_KEY in your environment for production use."
        )
        # Store with sentinel prefix so decrypt_payload can detect plaintext
        return {"_enc": False, "_data": payload}

    plaintext_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    token = fernet.encrypt(plaintext_bytes)
    return {"_enc": True, "_data": token.decode("utf-8")}


def decrypt_payload(stored: dict) -> dict:
    """
    SEC-002: Decrypt a stored credential payload dict after database retrieval.

    Handles both encrypted payloads and legacy/plaintext payloads transparently.
    """
    if not isinstance(stored, dict):
        return {}

    # Detect envelope format
    if "_enc" not in stored:
        # Legacy format — payload stored before encryption was added; return as-is
        logger.warning(
            "SEC-002: Credential payload has no encryption envelope (_enc key missing). "
            "This may be a legacy record stored before encryption was enabled. "
            "Re-save the credential to encrypt it."
        )
        return stored

    if not stored.get("_enc"):
        # Plaintext fallback (no key configured at time of storage)
        return stored.get("_data", {})

    # Encrypted path
    fernet = _get_fernet()
    if fernet is None:
        logger.critical(
            "SEC-002: Credential payload is encrypted but CREDENTIAL_ENCRYPTION_KEY is not set. "
            "Cannot decrypt. Configure the same key used for encryption."
        )
        return {}

    try:
        from cryptography.fernet import InvalidToken

        token_bytes = stored["_data"].encode("utf-8")
        plaintext_bytes = fernet.decrypt(token_bytes)
        return json.loads(plaintext_bytes.decode("utf-8"))
    except (InvalidToken, KeyError, json.JSONDecodeError) as exc:
        logger.error("SEC-002: Failed to decrypt credential payload: %s", exc.__class__.__name__)
        return {}
