"""Unit tests for credential redaction and privacy enforcement."""

from app.security import (
    redact_credentials,
    redact_share_link,
    redact_uuid,
    sanitize_server_address,
)


def test_redact_uuid():
    uuid = "12345678-1234-4234-8234-123456789abc"
    text = f"Connection error for user {uuid} on remote node"
    redacted = redact_uuid(text)
    assert uuid not in redacted
    assert "[REDACTED-UUID]" in redacted


def test_redact_credentials_passwords_and_tokens():
    text = (
        "Failed request with Authorization: Bearer ghp_1234567890abcdef12345678 "
        "connecting to vless://a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6@192.168.1.1:443"
    )
    redacted = redact_credentials(text)
    assert "ghp_" not in redacted
    assert "a1b2c3d4" not in redacted
    assert "[REDACTED-TOKEN]" in redacted
    assert "[REDACTED-AUTH]@" in redacted


def test_redact_reality_keys():
    text = "vless://node?security=reality&pbk=AbCdEfGhIjKlMnOpQrStUvWxYz123456&sid=12ab34cd"
    redacted = redact_credentials(text)
    assert "AbCdEfGhIjKl" not in redacted
    assert "[REDACTED-KEY]" in redacted
    assert "[REDACTED-SID]" in redacted


def test_redact_share_link():
    vless_link = "vless://7e1b5b24-9b16-4315-9923-b1d5d1c5d944@example.com:443?security=reality&pbk=1234567890123456789012#MyServer"
    redacted = redact_share_link(vless_link)
    assert "7e1b5b24" not in redacted
    assert "123456789012" not in redacted
    assert "example.com:443" in redacted
    assert "MyServer" in redacted


def test_redact_vmess_and_ss_base64():
    vmess_link = "vmess://eyJhZGQiOiIxLjEuMS4xIiwicG9ydCI6NDQzLCJpZCI6IjEyMzQ1Njc4In0="
    redacted = redact_share_link(vmess_link)
    assert "[ENCODED-CONFIG-REDACTED]" in redacted


def test_sanitize_server_address():
    addr = sanitize_server_address("1.2.3.4", 8080)
    assert addr == "1.2.3.4:8080"
