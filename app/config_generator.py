"""Minimal, secure Xray JSON configuration generator for candidate testing."""

import json
from typing import Any, Dict
from .config_parser.models import ProxyConfig


def generate_test_xray_config(config: ProxyConfig, socks_port: int) -> Dict[str, Any]:
    """
    Generate an isolated minimal Xray configuration JSON dictionary
    with a SOCKS5 inbound bound exclusively to 127.0.0.1 on socks_port.
    """
    if not (1024 <= socks_port <= 65535):
        raise ValueError(f"Invalid socks port: {socks_port}")

    # Build streamSettings
    stream_settings: Dict[str, Any] = {
        "network": config.network if config.network in ("tcp", "ws", "grpc", "http") else "tcp"
    }

    if config.security == "tls":
        stream_settings["security"] = "tls"
        tls_settings: Dict[str, Any] = {
            "serverName": config.sni or config.server,
            "allowInsecure": False,
        }
        if config.alpn:
            tls_settings["alpn"] = config.alpn
        if config.fingerprint:
            tls_settings["fingerprint"] = config.fingerprint
        stream_settings["tlsSettings"] = tls_settings

    elif config.security == "reality":
        stream_settings["security"] = "reality"
        reality_settings: Dict[str, Any] = {
            "serverName": config.sni or config.server,
            "fingerprint": config.fingerprint or "chrome",
            "show": False,
            "publicKey": config.public_key,
            "shortId": config.short_id,
            "spiderX": config.spider_x or "/",
        }
        stream_settings["realitySettings"] = reality_settings

    # Network-specific streamSettings
    if config.network == "ws":
        ws_settings: Dict[str, Any] = {
            "path": config.ws_path or "/",
            "headers": config.ws_headers if config.ws_headers else {},
        }
        stream_settings["wsSettings"] = ws_settings
    elif config.network == "grpc":
        grpc_settings: Dict[str, Any] = {
            "serviceName": config.grpc_service_name or "",
            "multiMode": (config.grpc_mode.lower() == "multi"),
        }
        stream_settings["grpcSettings"] = grpc_settings

    # Outbound protocol definitions
    protocol = config.protocol.lower()
    outbound: Dict[str, Any] = {"tag": "proxy"}

    if protocol == "vless":
        outbound["protocol"] = "vless"
        user_entry: Dict[str, Any] = {
            "id": config.uuid,
            "encryption": "none",
        }
        if config.flow:
            user_entry["flow"] = config.flow
        outbound["settings"] = {
            "vnext": [{
                "address": config.server,
                "port": config.port,
                "users": [user_entry],
            }]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "vmess":
        outbound["protocol"] = "vmess"
        outbound["settings"] = {
            "vnext": [{
                "address": config.server,
                "port": config.port,
                "users": [{
                    "id": config.uuid,
                    "alterId": config.alter_id,
                    "security": config.cipher or "auto",
                }],
            }]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "trojan":
        outbound["protocol"] = "trojan"
        outbound["settings"] = {
            "servers": [{
                "address": config.server,
                "port": config.port,
                "password": config.password,
            }]
        }
        outbound["streamSettings"] = stream_settings

    elif protocol == "shadowsocks":
        outbound["protocol"] = "shadowsocks"
        outbound["settings"] = {
            "servers": [{
                "address": config.server,
                "port": config.port,
                "method": config.cipher or "aes-256-gcm",
                "password": config.password,
            }]
        }

    else:
        raise ValueError(f"Unsupported protocol for Xray configuration generator: {protocol}")

    xray_config: Dict[str, Any] = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [{
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "port": socks_port,
            "protocol": "socks",
            "settings": {
                "auth": "noauth",
                "udp": True,
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            }
        }],
        "outbounds": [
            outbound,
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ],
    }

    return xray_config
