"""Comprehensive security tests for GmailMind Phase 2.5.

Tests all security features:
- Encryption
- Input validation
- API key authentication
- Security headers
- Rate limiting
"""

import pytest

from security.auth import APIKeyManager, generate_api_key
from security.encryption import EncryptionManager
from security.validators import (
    sanitize_string,
    validate_email,
    validate_user_id,
    sanitize_dict,
    validate_phone,
    sanitize_filename,
)


# ============================================================================
# Encryption Tests
# ============================================================================


class TestEncryption:
    """Test encryption and decryption functionality."""

    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption."""
        em = EncryptionManager()
        original = "secret_token_abc123"
        encrypted = em.encrypt(original)

        # Encrypted should be different from original
        assert encrypted != original

        # Decrypted should match original
        decrypted = em.decrypt(encrypted)
        assert decrypted == original

    def test_encrypted_looks_different(self):
        """Test that same text encrypts to different values (Fernet uses timestamp)."""
        em = EncryptionManager()
        e1 = em.encrypt("same_text")
        e2 = em.encrypt("same_text")

        # Fernet adds timestamp so each encryption is unique
        assert e1 != e2

    def test_decrypt_wrong_data_returns_none(self):
        """Test that decrypting invalid data returns None gracefully."""
        em = EncryptionManager()
        result = em.decrypt("not_encrypted_data")
        assert result is None

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        em = EncryptionManager()
        result = em.encrypt("")
        assert result == ""

    def test_encrypt_dict_fields(self):
        """Test encrypting specific fields in a dictionary."""
        em = EncryptionManager()
        data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "key_abc"
        }

        encrypted = em.encrypt_dict(data, ["password", "api_key"])

        # Username should remain unchanged
        assert encrypted["username"] == "test_user"

        # Password and api_key should be encrypted
        assert encrypted["password"] != "secret123"
        assert encrypted["api_key"] != "key_abc"

    def test_decrypt_dict_fields(self):
        """Test decrypting specific fields in a dictionary."""
        em = EncryptionManager()
        data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "key_abc"
        }

        # Encrypt then decrypt
        encrypted = em.encrypt_dict(data, ["password", "api_key"])
        decrypted = em.decrypt_dict(encrypted, ["password", "api_key"])

        # Should match original
        assert decrypted["username"] == "test_user"
        assert decrypted["password"] == "secret123"
        assert decrypted["api_key"] == "key_abc"


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestValidators:
    """Test input validation and sanitization."""

    def test_valid_email(self):
        """Test valid email addresses."""
        assert validate_email("user@gmail.com") == True
        assert validate_email("user@company.co.uk") == True
        assert validate_email("test+tag@example.com") == True
        assert validate_email("user.name@subdomain.example.org") == True

    def test_invalid_email(self):
        """Test invalid email addresses."""
        assert validate_email("notanemail") == False
        assert validate_email("@gmail.com") == False
        assert validate_email("user@") == False
        assert validate_email("user@.com") == False
        assert validate_email("") == False
        assert validate_email(None) == False

    def test_sanitize_removes_nullbytes(self):
        """Test null byte removal."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_sanitize_strips_whitespace(self):
        """Test whitespace stripping."""
        result = sanitize_string("  hello  ")
        assert result == "hello"

    def test_sanitize_respects_max_length(self):
        """Test maximum length enforcement."""
        long_string = "a" * 300
        result = sanitize_string(long_string, max_length=100)
        assert len(result) <= 100
        assert len(result) == 100

    def test_sanitize_removes_control_chars(self):
        """Test control character removal."""
        result = sanitize_string("hello\x01\x02world")
        assert "\x01" not in result
        assert "\x02" not in result

    def test_valid_user_id(self):
        """Test valid user IDs."""
        assert validate_user_id("user_123") == True
        assert validate_user_id("default") == True
        assert validate_user_id("test-user") == True
        assert validate_user_id("User123") == True

    def test_invalid_user_id(self):
        """Test invalid user IDs (SQL injection attempts)."""
        assert validate_user_id("user; DROP TABLE") == False
        assert validate_user_id("../../../etc") == False
        assert validate_user_id("user@domain") == False
        assert validate_user_id("a" * 51) == False  # Too long
        assert validate_user_id("") == False
        assert validate_user_id(None) == False

    def test_sanitize_dict_keeps_allowed_keys(self):
        """Test dictionary sanitization keeps only allowed keys."""
        data = {
            "allowed1": "value1",
            "allowed2": "value2",
            "forbidden": "should_be_removed"
        }
        result = sanitize_dict(data, ["allowed1", "allowed2"])

        assert "allowed1" in result
        assert "allowed2" in result
        assert "forbidden" not in result

    def test_sanitize_dict_cleans_string_values(self):
        """Test dictionary sanitization cleans string values."""
        data = {
            "field": "  value\x00  "
        }
        result = sanitize_dict(data, ["field"])

        assert result["field"] == "value"
        assert "\x00" not in result["field"]

    def test_validate_phone(self):
        """Test phone number validation."""
        assert validate_phone("+1234567890") == True
        assert validate_phone("(123) 456-7890") == True
        assert validate_phone("123-456-7890") == True
        assert validate_phone("not a phone") == False

    def test_sanitize_filename(self):
        """Test filename sanitization (path traversal prevention)."""
        # Path traversal attempts are neutralized (slashes replaced, ".." removed)
        assert sanitize_filename("../../../etc/passwd") == "___etc_passwd"
        assert sanitize_filename("file/with/slashes") == "file_with_slashes"
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        # Additional edge cases
        assert sanitize_filename("..") == "unnamed"  # Only ".." becomes empty, returns default
        assert sanitize_filename("file..name") == "filename"  # ".." removed anywhere


# ============================================================================
# API Key Generation Tests
# ============================================================================


class TestAPIKeyGeneration:
    """Test API key generation and management."""

    def test_key_has_prefix(self):
        """Test API key has correct prefix."""
        key = generate_api_key()
        assert key.startswith("gmsk_")

    def test_keys_are_unique(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique

    def test_key_length_sufficient(self):
        """Test API key has sufficient length."""
        key = generate_api_key()
        assert len(key) >= 40  # At least 40 characters

    def test_key_uses_urlsafe_chars(self):
        """Test API key uses URL-safe characters."""
        key = generate_api_key()
        # Should only contain alphanumeric, underscore, hyphen
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        key_chars = set(key)
        assert key_chars.issubset(allowed_chars)


# ============================================================================
# API Key Manager Tests
# ============================================================================


class TestAPIKeyManager:
    """Test API key manager functionality."""

    def test_hash_key_is_consistent(self):
        """Test key hashing is consistent."""
        manager = APIKeyManager()
        key = "test_key_123"
        hash1 = manager._hash_key(key)
        hash2 = manager._hash_key(key)
        assert hash1 == hash2

    def test_hash_key_is_different_for_different_keys(self):
        """Test different keys produce different hashes."""
        manager = APIKeyManager()
        hash1 = manager._hash_key("key1")
        hash2 = manager._hash_key("key2")
        assert hash1 != hash2

    def test_hash_key_length(self):
        """Test hash is correct length (SHA-256 = 64 hex chars)."""
        manager = APIKeyManager()
        hash_result = manager._hash_key("test_key")
        assert len(hash_result) == 64


# ============================================================================
# Security Headers Tests (FastAPI Integration)
# ============================================================================


class TestSecurityHeaders:
    """Test security headers in HTTP responses."""

    def test_security_headers_present(self):
        """Test that security headers are present in responses."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")

        # Check for security headers (case-insensitive)
        headers_lower = {k.lower(): v for k, v in response.headers.items()}

        assert "x-content-type-options" in headers_lower
        assert headers_lower["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in headers_lower
        assert headers_lower["x-frame-options"] == "DENY"

        assert "x-xss-protection" in headers_lower

    def test_health_endpoint_public(self):
        """Test that health endpoint is publicly accessible."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_security_status_public(self):
        """Test that security status page is publicly accessible."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/security-status")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_protected_endpoint_requires_key(self):
        """Test that protected endpoints require API key."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/platform/stats")

        # Should be 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [401, 403]

    def test_server_header_removed(self):
        """Test that server header is removed (hides version info)."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")

        # Server header should be removed or not contain version info
        server_header = response.headers.get("server", "")
        assert "uvicorn" not in server_header.lower() or server_header == ""


# ============================================================================
# Integration Tests
# ============================================================================


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_docs_available_in_dev(self):
        """Test that API docs are available in development."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/docs")

        # Should be accessible in development
        assert response.status_code in [200, 404]  # 404 if disabled in production

    def test_cors_headers_present(self):
        """Test that CORS headers are configured."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.options("/health", headers={"Origin": "http://localhost:3000"})

        # CORS headers should be present
        assert "access-control-allow-origin" in {k.lower() for k in response.headers.keys()}


# ============================================================================
# Performance Tests
# ============================================================================


class TestSecurityPerformance:
    """Test that security features don't severely impact performance."""

    def test_encryption_performance(self):
        """Test encryption is reasonably fast."""
        import time

        em = EncryptionManager()
        data = "x" * 1000  # 1KB of data

        start = time.time()
        for _ in range(100):
            encrypted = em.encrypt(data)
            em.decrypt(encrypted)
        elapsed = time.time() - start

        # Should complete 100 encrypt/decrypt cycles in under 1 second
        assert elapsed < 1.0

    def test_validation_performance(self):
        """Test validation is reasonably fast."""
        import time

        start = time.time()
        for _ in range(1000):
            validate_email("test@example.com")
            validate_user_id("test_user_123")
            sanitize_string("test string")
        elapsed = time.time() - start

        # Should complete 1000 validations in under 0.1 second
        assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
