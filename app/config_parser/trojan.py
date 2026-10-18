"""Parser for Trojan share links."""

import urllib.parse
from .models import ProxyConfig


def parse_trojan(link: str) -> ProxyConfig:
    """
    Parse a trojan:// share link into a ProxyConfig object.
    Format: trojan://password@host:port?query_params#remark
    """
    link = link.strip()
    if not link.startswith("trojan://"):
        raise ValueError("Link must start with 'trojan://'")

    parsed = urllib.parse.urlsplit(link)

    netloc = parsed.netloc
    if "@" not in netloc:
        raise ValueError("Malformed Trojan link: missing '@' separating password and server")

    password_part, host_port = netloc.split("@", 1)
    password = urllib.parse.unquote(password_part).strip()
    if not password:
        raise ValueError("Trojan configuration is missing a password")

    if ":" not in host_port:
        raise ValueError("Malformed Trojan link: missing port in host specification")

    if host_port.startswith("[") and "]" in host_port:
        bracket_end = host_port.find("]")
        host = host_port[1:bracket_end]
        port_str = host_port[bracket_end + 1:].lstrip(":")
    else:
        host, port_str = host_port.rsplit(":", 1)

    host = host.strip()
    if not host:
        raise ValueError("Trojan configuration is missing a host/IP")

    try:
        port = int(port_str.strip())
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        raise ValueError(f"Invalid port '{port_str}' in Trojan configuration")

    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    def get_first(key: str, default: str = "") -> str:
        vals = params.get(key, [])
        return vals[0].strip() if vals else default

    network = get_first("type", get_first("net", "tcp")).lower()
    security = get_first("security", "tls").lower()  # Trojan defaults to TLS
    sni = get_first("sni", get_first("peer", host))
    fingerprint = get_first("fp", "")
    ws_path = get_first("path", "")
    ws_host = get_first("host", "")
    grpc_service = get_first("serviceName", "")
    grpc_mode = get_first("mode", "gun")

    alpn_raw = get_first("alpn", "")
    alpn = [s.strip() for s in alpn_raw.split(",") if s.strip()] if alpn_raw else []

    ws_headers = {}
    if ws_host:
        ws_headers["Host"] = ws_host

    remark = urllib.parse.unquote(parsed.fragment).strip() if parsed.fragment else ""

    known_keys = {
        "type", "net", "security", "sni", "peer", "fp", "path", "host",
        "serviceName", "mode", "alpn", "headerType"
    }
    extra = {k: v[0] for k, v in params.items() if k not in known_keys and v}

    return ProxyConfig(
        protocol="trojan",
        server=host,
        port=port,
        name=remark,
        password=password,
        network=network,
        security=security,
        sni=sni,
        alpn=alpn,
        fingerprint=fingerprint,
        ws_path=ws_path,
        ws_headers=ws_headers,
        grpc_service_name=grpc_service,
        grpc_mode=grpc_mode,
        raw_link=link,
        extra=extra,
    )
