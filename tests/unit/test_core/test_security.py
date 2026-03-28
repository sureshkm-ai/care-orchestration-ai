"""Tests for security layer: auth, rbac, encryption, redaction."""

from __future__ import annotations

import pytest

from src.core.errors import AuthorizationError
from src.core.security.auth import (
    create_access_token,
    get_agent_token,
    require_scope,
    verify_token,
)
from src.core.security.encryption import decrypt_phi, encrypt_phi
from src.core.security.rbac import AgentRole, get_role_scopes, has_permission, require_permission
from src.core.security.redaction import redact_dict, redact_string, sanitize_exception


class TestJWTAuth:
    def test_create_and_verify_token(self) -> None:
        token = create_access_token("triage_agent", ["patient:read", "triage:write"])
        payload = verify_token(token)
        assert payload.sub == "triage_agent"
        assert "patient:read" in payload.scopes
        assert "triage:write" in payload.scopes

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(AuthorizationError, match="Invalid token"):
            verify_token("invalid.token.here")

    def test_require_scope_passes(self) -> None:
        token = create_access_token("test", ["patient:read"])
        payload = verify_token(token)
        require_scope(payload, "patient:read")  # Should not raise

    def test_require_scope_fails(self) -> None:
        token = create_access_token("test", ["patient:read"])
        payload = verify_token(token)
        with pytest.raises(AuthorizationError, match="lacks required scope"):
            require_scope(payload, "patient:write")

    def test_get_agent_token(self) -> None:
        token = get_agent_token("triage_agent")
        payload = verify_token(token)
        assert payload.sub == "triage_agent"
        assert "patient:read" in payload.scopes


class TestRBAC:
    def test_triage_has_patient_read(self) -> None:
        assert has_permission(AgentRole.TRIAGE, "patient:read")

    def test_triage_lacks_appointment_write(self) -> None:
        assert not has_permission(AgentRole.TRIAGE, "appointment:write")

    def test_require_permission_passes(self) -> None:
        require_permission(AgentRole.CARE_COORDINATOR, "appointment:write")

    def test_require_permission_fails(self) -> None:
        with pytest.raises(AuthorizationError):
            require_permission(AgentRole.TRIAGE, "appointment:write")

    def test_get_role_scopes(self) -> None:
        scopes = get_role_scopes(AgentRole.TRIAGE)
        assert isinstance(scopes, list)
        assert "patient:read" in scopes


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        plaintext = "John Doe SSN: 123-45-6789"
        ciphertext = encrypt_phi(plaintext)
        assert ciphertext != plaintext
        assert decrypt_phi(ciphertext) == plaintext

    def test_empty_string_passthrough(self) -> None:
        assert encrypt_phi("") == ""
        assert decrypt_phi("") == ""


class TestRedaction:
    def test_redact_ssn(self) -> None:
        text = "Patient SSN is 123-45-6789"
        assert "[REDACTED-SSN]" in redact_string(text)

    def test_redact_email(self) -> None:
        text = "Contact: john@hospital.com"
        assert "[REDACTED-EMAIL]" in redact_string(text)

    def test_redact_dict_sensitive_keys(self) -> None:
        data = {"patient_name": "John Doe", "urgency": "high"}
        result = redact_dict(data)
        assert result["patient_name"] == "[REDACTED]"
        assert result["urgency"] == "high"

    def test_redact_dict_nested(self) -> None:
        data = {"patient": {"name": "Jane", "ssn": "999-88-7777"}}
        result = redact_dict(data)
        assert result["patient"]["name"] == "[REDACTED]"

    def test_sanitize_exception(self) -> None:
        exc = ValueError("Patient SSN 123-45-6789 not found")
        sanitized = sanitize_exception(exc)
        assert "123-45-6789" not in sanitized
        assert "[REDACTED-SSN]" in sanitized
