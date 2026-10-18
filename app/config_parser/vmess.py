"""Parser for VMess share links (Base64 JSON and URL formats)."""

import base64
import json
import urllib.parse
from typing import Any, Dict
from .models import ProxyConfig


def safe_b64decode(encoded: str) -> str:
    """Safely decode base64 string handling missing padding and URL-safe chars."""
    s = encoded.strip().replace("-", "+").replace("_", "/")
    padding = (4 - len(s) % 4) % 4
    s += "=" * padding
    raw_bytes = base64.b64decode(s)
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def parse_vmess(link: str) -> ProxyConfig:
    """
    Parse a vmess:// share link.
    Supports both standard Base64-JSON (vmess://<b64>) and URI formats.
    """
    link = link.strip()
    if not link.startswith("vmess://"):
        raise ValueError("Link must start with 'vmess://'")

    content = link[8:].strip()

    # If it contains '@' or looks like a URL
    if "@" in content:
        return _parse_vmess_uri(link)

    # Standard VMess Base64-encoded JSON format
    # Strip any trailing fragment if present
    if "#" in content:
        b64_part, remark_from_fragment = content.split("#", 1)
        remark_from_fragment = urllib.parse.unquote(remark_from_fragment).strip()
    else:
        b64_part = content
        remark_from_fragment = ""

    try:
        decoded_text = safe_b64decode(b64_part)
        data = json.loads(decoded_text)
    except Exception as e:
        raise ValueError(f"Failed to decode VMess Base64 JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError("Decoded VMess content is not a valid JSON object")

    server = str(data.get("add", "")).strip()
    if not server:
        raise ValueError("VMess configuration is missing server address ('add')")

    port_raw = data.get("port")
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(f"Invalid port '{port_raw}' in VMess configuration")

    uuid = str(data.get("id", "")).strip()
    if not uuid:
        raise ValueError("VMess configuration is missing UUID ('id')")

    alter_id_raw = data.get("aid", 0)
    try:
        alter_id = int(alter_id_raw)
    except (ValueError, TypeError):
        alter_id = 0

    network = str(data.get("net", "tcp")).strip().lower()
    type_header = str(data.get("type", "none")).strip().lower()
    security = "tls" if str(data.get("tls", "")).strip().lower() in ("tls", "1", "true") else "none"

    cipher = str(data.get("scy", data.get("cipher", "auto"))).strip().lower()
    if cipher not in ("auto", "aes-128-gcm", "chacha20-poly1305", "none", "zero"):
        cipher = "auto"

    sni = str(data.get("sni", "")).strip()
    host = str(data.get("host", "")).strip()
    if not sni and host and security == "tls":
        sni = host

    path = str(data.get("path", "")).strip()
    name = remark_from_fragment or str(data.get("ps", "")).strip()
    alpn_raw = data.get("alpn", "")
    if isinstance(alpn_raw, list):
        alpn = [str(a).strip() for a in alpn_raw]
    elif isinstance(alpn_raw, str) and alpn_raw:
        alpn = [s.strip() for s in alpn_raw.split(",") if s.strip()]
    else:
        alpn = []

    fingerprint = str(data.get("fp", "")).strip()

    ws_headers = {}
    if host:
        ws_headers["Host"] = host

    grpc_service = ""
    if network == "grpc":
        grpc_service = path or str(data.get("serviceName", "")).strip()

    extra = {k: v for k, v in data.items() if k not in {
        "v", "ps", "add", "port", "id", "aid", "scy", "cipher", "net",
        "type", "host", "path", "tls", "sni", "alpn", "fp"
    }}

    return ProxyConfig(
        protocol="vmess",
        server=server,
        port=port,
        name=name,
        uuid=uuid,
        alter_id=alter_id,
        cipher=cipher,
        network=network,
        security=security,
        sni=sni,
        alpn=alpn,
        fingerprint=fingerprint,
        ws_path=path,
        ws_headers=ws_headers,
        grpc_service_name=grpc_service,
        raw_link=link,
        extra=extra,
    )


def _parse_vmess_uri(link: str) -> ProxyConfig:
    """Parse vmess:// link structured like a URI."""
    parsed = urllib.parse.urlsplit(link)
    netloc = parsed.netloc
    uuid_part, host_port = netloc.split("@", 1)
    uuid = urllib.parse.unquote(uuid_part).strip()

    if ":" not in host_port:
        raise ValueError("Missing port in VMess URI")

    if host_port.startswith("[") and "]" in host_port:
        bracket_end = host_port.find("]")
        host = host_port[1:bracket_end]
        port_str = host_port[bracket_end + 1:].lstrip(":")
    else:
        host, port_str = host_port.rsplit(":", 1)

    port = int(port_str.strip())
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    def get_first(key: str, default: str = "") -> str:
        vals = params.get(key, [])
        return vals[0].strip() if vals else default

    network = get_first("type", get_first("net", "tcp")).lower()
    security = get_first("security", "none").lower()
    sni = get_first("sni", "")
    remark = urllib.parse.unquote(parsed.fragment).strip() if parsed.fragment else ""

    return ProxyConfig(
        protocol="vmess",
        server=host,
        port=port,
        name=remark,
        uuid=uuid,
        network=network,
        security=security,
        sni=sni,
        raw_link=link,
    )
