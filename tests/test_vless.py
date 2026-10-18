"""Unit tests for VLESS share link parsing and validation."""

import pytest
from app.config_parser.vless import parse_vless


def test_parse_vless_reality():
    link = (
        "vless://9a8b7c6d-1234-5678-9abc-def012345678@node.example.com:443"
        "?type=tcp&security=reality&pbk=12345678901234567890123456789012&fp=chrome"
        "&sni=www.microsoft.com&sid=1234abcd&spx=%2F&flow=xtls-rprx-vision#Node%20US"
    )
    config = parse_vless(link)
    assert config.protocol == "vless"
    assert config.server == "node.example.com"
    assert config.port == 443
    assert config.uuid == "9a8b7c6d-1234-5678-9abc-def012345678"
    assert config.security == "reality"
    assert config.public_key == "12345678901234567890123456789012"
    assert config.fingerprint == "chrome"
    assert config.sni == "www.microsoft.com"
    assert config.short_id == "1234abcd"
    assert config.spider_x == "/"
    assert config.flow == "xtls-rprx-vision"
    assert config.name == "Node US"


def test_parse_vless_websocket():
    link = (
        "vless://user-uuid-1234@192.168.1.1:8080"
        "?type=ws&security=none&path=%2Fchat&host=speed.cloudflare.com#My%20WS"
    )
    config = parse_vless(link)
    assert config.protocol == "vless"
    assert config.server == "192.168.1.1"
    assert config.port == 8080
    assert config.network == "ws"
    assert config.ws_path == "/chat"
    assert config.ws_headers.get("Host") == "speed.cloudflare.com"
    assert config.name == "My WS"


def test_parse_vless_ipv6():
    link = "vless://my-uuid@[2001:db8::1]:8443?security=tls#IPv6%20Node"
    config = parse_vless(link)
    assert config.server == "2001:db8::1"
    assert config.port == 8443
    assert config.security == "tls"
    assert config.name == "IPv6 Node"


def test_parse_vless_malformed():
    with pytest.raises(ValueError, match="missing '@'"):
        parse_vless("vless://invalid_no_at_sign")

    with pytest.raises(ValueError, match="missing port"):
        parse_vless("vless://uuid@host_without_port")

    with pytest.raises(ValueError, match="Invalid port"):
        parse_vless("vless://uuid@host:999999")

    with pytest.raises(ValueError, match="missing a UUID"):
        parse_vless("vless://@host:443")
