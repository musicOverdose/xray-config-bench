"""Parser for VLESS share links."""

import urllib.parse
from typing import Optional
from .models import ProxyConfig
from ..security import redact_credentials


def parse_vless(link: str) -> ProxyConfig:
    """
    Parse a vless:// share link into a ProxyConfig object.
    Format: vless://uuid@host:port?query_params#remark
    """
    link = link.strip()
    if not link.startswith("vless://"):
        raise ValueError("Link must start with 'vless://'")

    parsed = urllib.parse.urlsplit(link)

    # Netloc contains uuid@host:port
    netloc = parsed.netloc
    if "@" not in netloc:
        raise ValueError("Malformed VLESS link: missing '@' separating UUID and server")

    uuid_part, host_port = netloc.split("@", 1)
    uuid = urllib.parse.unquote(uuid_part).strip()
    if not uuid:
        raise ValueError("VLESS configuration is missing a UUID")

    # Host and port
    if ":" not in host_port:
        raise ValueError("Malformed VLESS link: missing port in host specification")

    # Handle IPv6 addresses [::1]:port
    if host_port.startswith("[") and "]" in host_port:
        bracket_end = host_port.find("]")
        host = host_port[1:bracket_end]
        port_str = host_port[bracket_end + 1:].lstrip(":")
    else:
        host, port_str = host_port.rsplit(":", 1)

    host = host.strip()
    if not host:
        raise ValueError("VLESS configuration is missing a host/IP")

    try:
        port = int(port_str.strip())
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        raise ValueError(f"Invalid port '{port_str}' in VLESS configuration")

    # Query parameters
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    def get_first(key: str, default: str = "") -> str:
        vals = params.get(key, [])
        return vals[0].strip() if vals else default

    network = get_first("type", get_first("net", "tcp")).lower()
    security = get_first("security", "none").lower()
    flow = get_first("flow", "")
    sni = get_first("sni", "")
    fingerprint = get_first("fp", "")
    public_key = get_first("pbk", "")
    short_id = get_first("sid", "")
    spider_x = get_first("spx", "")
    ws_path = get_first("path", "")
    ws_host = get_first("host", "")
    grpc_service = get_first("serviceName", "")
    grpc_mode = get_first("mode", "gun")

    alpn_raw = get_first("alpn", "")
    alpn = [s.strip() for s in alpn_raw.split(",") if s.strip()] if alpn_raw else []

    ws_headers = {}
    if ws_host:
        ws_headers["Host"] = ws_host

    # Remark / name from URL fragment
    remark = urllib.parse.unquote(parsed.fragment).strip() if parsed.fragment else ""

    # Extra parameters preserved
    known_keys = {
        "type", "net", "security", "flow", "sni", "fp", "pbk", "sid", "spx",
        "path", "host", "serviceName", "mode", "alpn", "headerType"
    }
    extra = {k: v[0] for k, v in params.items() if k not in known_keys and v}

    return ProxyConfig(
        protocol="vless",
        server=host,
        port=port,
        name=remark,
        uuid=uuid,
        network=network,
        security=security,
        sni=sni,
        alpn=alpn,
        fingerprint=fingerprint,
        flow=flow,
        public_key=public_key,
        short_id=short_id,
        spider_x=spider_x,
        ws_path=ws_path,
        ws_headers=ws_headers,
        grpc_service_name=grpc_service,
        grpc_mode=grpc_mode,
        raw_link=link,
        extra=extra,
    )
