"""Parser for Shadowsocks (SIP002 and legacy) share links."""

import base64
import urllib.parse
from .models import ProxyConfig
from .vmess import safe_b64decode


def parse_shadowsocks(link: str) -> ProxyConfig:
    """
    Parse a ss:// share link.
    Supports SIP002 (ss://base64(method:password)@server:port#remark)
    and legacy format (ss://base64(method:password@server:port)#remark).
    """
    link = link.strip()
    if not link.startswith("ss://"):
        raise ValueError("Link must start with 'ss://'")

    content = link[5:].strip()

    # Extract fragment (remark)
    if "#" in content:
        main_part, remark_encoded = content.split("#", 1)
        remark = urllib.parse.unquote(remark_encoded).strip()
    else:
        main_part = content
        remark = ""

    # Check if SIP002 format with '@'
    if "@" in main_part:
        # SIP002: ss://base64(method:password)@host:port/?plugin=...
        userinfo, host_port_query = main_part.split("@", 1)

        # Decode userinfo (may be base64 or plaintext method:password)
        if ":" in userinfo:
            cipher, password = userinfo.split(":", 1)
        else:
            try:
                decoded_userinfo = safe_b64decode(userinfo)
                if ":" in decoded_userinfo:
                    cipher, password = decoded_userinfo.split(":", 1)
                else:
                    raise ValueError("Missing colon in decoded Shadowsocks userinfo")
            except Exception as e:
                raise ValueError(f"Failed to decode Shadowsocks userinfo: {e}")

        # Parse host, port, query
        if "/" in host_port_query:
            host_port, query_part = host_port_query.split("/", 1)
            query_part = query_part.lstrip("?")
        elif "?" in host_port_query:
            host_port, query_part = host_port_query.split("?", 1)
        else:
            host_port = host_port_query
            query_part = ""

        if ":" not in host_port:
            raise ValueError("Missing port in Shadowsocks host specification")

        if host_port.startswith("[") and "]" in host_port:
            bracket_end = host_port.find("]")
            host = host_port[1:bracket_end]
            port_str = host_port[bracket_end + 1:].lstrip(":")
        else:
            host, port_str = host_port.rsplit(":", 1)

        port = int(port_str.strip())

        # Check for plugin query parameters
        plugin_info = {}
        if query_part:
            params = urllib.parse.parse_qs(query_part)
            plugin_val = params.get("plugin", [""])[0]
            if plugin_val:
                plugin_info["plugin"] = urllib.parse.unquote(plugin_val)

    else:
        # Legacy format: ss://base64(method:password@host:port)
        try:
            decoded = safe_b64decode(main_part)
        except Exception as e:
            raise ValueError(f"Failed to decode legacy Shadowsocks link: {e}")

        if "@" not in decoded:
            raise ValueError("Malformed legacy Shadowsocks link: missing '@'")

        userinfo, host_port = decoded.split("@", 1)
        if ":" not in userinfo:
            raise ValueError("Malformed legacy Shadowsocks userinfo: missing ':'")

        cipher, password = userinfo.split(":", 1)

        if ":" not in host_port:
            raise ValueError("Malformed legacy Shadowsocks host: missing port")

        if host_port.startswith("[") and "]" in host_port:
            bracket_end = host_port.find("]")
            host = host_port[1:bracket_end]
            port_str = host_port[bracket_end + 1:].lstrip(":")
        else:
            host, port_str = host_port.rsplit(":", 1)

        port = int(port_str.strip())
        plugin_info = {}

    host = host.strip()
    cipher = cipher.strip()
    password = password.strip()

    if not host:
        raise ValueError("Shadowsocks configuration is missing host/IP")
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid port '{port}' in Shadowsocks configuration")
    if not cipher:
        raise ValueError("Shadowsocks configuration is missing cipher/method")
    if not password:
        raise ValueError("Shadowsocks configuration is missing password")

    return ProxyConfig(
        protocol="shadowsocks",
        server=host,
        port=port,
        name=remark,
        password=password,
        cipher=cipher,
        network="tcp",
        raw_link=link,
        extra=plugin_info,
    )
