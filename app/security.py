"""Security and privacy utilities for redacting sensitive credentials."""

import re
from typing import Optional

# Pattern for UUIDv4 / UUID format: 8-4-4-4-12 hex characters
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# Pattern for IPv4/IPv6 and ports
IP_PORT_PATTERN = re.compile(r"(\b(?:\d{1,3}\.){3}\d{1,3}):(\d{1,5})\b")

# Pattern for userinfo in URLs (e.g., protocol://user:pass@host or protocol://uuid@host)
URL_USERINFO_PATTERN = re.compile(
    r"((?:vless|vmess|trojan|ss|http|https|socks5)://)([^@/]+)@"
)

# Pattern for Reality public key / short id
REALITY_KEY_PATTERN = re.compile(r"(pbk=)[a-zA-Z0-9_-]{20,}", re.IGNORECASE)
REALITY_SID_PATTERN = re.compile(r"(sid=)[a-zA-Z0-9]{4,}", re.IGNORECASE)

# Pattern for Bearer / GitHub tokens: ghp_..., gho_..., github_pat_...
TOKEN_PATTERN = re.compile(
    r"(?:ghp|gho|ghu|ghs|ghr|github_pat)_[a-zA-Z0-9_]{16,}", re.IGNORECASE
)

# Pattern for Authorization headers
AUTH_HEADER_PATTERN = re.compile(
    r"(Authorization:\s*(?:Bearer|token)\s+)[^\r\n\s]+", re.IGNORECASE
)


def redact_uuid(text: str) -> str:
    """Replace all UUID instances with a redacted placeholder."""
    return UUID_PATTERN.sub("[REDACTED-UUID]", text)


def redact_credentials(text: str) -> str:
    """
    Thoroughly redact credentials (passwords, UUIDs, tokens, Reality keys)
    from log strings, error messages, or diagnostic dumps.
    """
    if not text:
        return ""

    # Redact Authorization header values
    text = AUTH_HEADER_PATTERN.sub(r"\1[REDACTED-TOKEN]", text)

    # Redact GitHub / API tokens
    text = TOKEN_PATTERN.sub("[REDACTED-TOKEN]", text)

    # Redact UUIDs
    text = UUID_PATTERN.sub("[REDACTED-UUID]", text)

    # Redact URL userinfo
    text = URL_USERINFO_PATTERN.sub(r"\1[REDACTED-AUTH]@", text)

    # Redact Reality sensitive parameters
    text = REALITY_KEY_PATTERN.sub(r"\1[REDACTED-KEY]", text)
    text = REALITY_SID_PATTERN.sub(r"\1[REDACTED-SID]", text)

    return text


def redact_share_link(link: str) -> str:
    """
    Produce a safe representation of a share link for logging or display
    where credentials cannot be leaked.
    """
    if not link:
        return ""

    # For vless://uuid@host:port or trojan://password@host:port
    redacted = URL_USERINFO_PATTERN.sub(r"\1[REDACTED-AUTH]@", link)
    redacted = redact_uuid(redacted)
    redacted = REALITY_KEY_PATTERN.sub(r"\1[REDACTED-KEY]", redacted)
    redacted = REALITY_SID_PATTERN.sub(r"\1[REDACTED-SID]", redacted)

    # For vmess://base64 or ss://base64
    if redacted.startswith("vmess://") and len(redacted) > 16:
        # Don't show full base64 in logs
        return "vmess://[ENCODED-CONFIG-REDACTED]"
    if redacted.startswith("ss://") and "@" not in redacted and len(redacted) > 16:
        return "ss://[ENCODED-CONFIG-REDACTED]"

    return redacted


def sanitize_server_address(server: str, port: int) -> str:
    """Return a clean representation of a server address."""
    return f"{server}:{port}"
