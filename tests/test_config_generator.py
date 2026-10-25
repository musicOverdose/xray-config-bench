"""Unit tests for minimal Xray JSON config generation."""

import pytest
from app.config_generator import generate_test_xray_config
from app.config_parser.vless import parse_vless
from app.config_parser.trojan import parse_trojan


def test_generate_vless_reality_config():
    link = (
        "vless://9a8b7c6d-1234-5678-9abc-def012345678@node.example.com:443"
        "?type=tcp&security=reality&pbk=12345678901234567890123456789012&fp=chrome"
        "&sni=www.microsoft.com&sid=1234abcd&flow=xtls-rprx-vision#US"
    )
    cfg = parse_vless(link)
    xray_json = generate_test_xray_config(cfg, socks_port=10808)

    # Inbound verification
    inbounds = xray_json["inbounds"]
    assert len(inbounds) == 1
    assert inbounds[0]["protocol"] == "socks"
    assert inbounds[0]["listen"] == "127.0.0.1"  # CRITICAL: Local only!
    assert inbounds[0]["port"] == 10808

    # Outbound verification
    outbounds = xray_json["outbounds"]
    proxy_out = outbounds[0]
    assert proxy_out["protocol"] == "vless"
    assert proxy_out["settings"]["vnext"][0]["address"] == "node.example.com"
    assert proxy_out["settings"]["vnext"][0]["port"] == 443
    user = proxy_out["settings"]["vnext"][0]["users"][0]
    assert user["id"] == "9a8b7c6d-1234-5678-9abc-def012345678"
    assert user["flow"] == "xtls-rprx-vision"

    # Reality streamSettings
    stream = proxy_out["streamSettings"]
    assert stream["security"] == "reality"
    assert stream["realitySettings"]["serverName"] == "www.microsoft.com"
    assert stream["realitySettings"]["publicKey"] == "12345678901234567890123456789012"
    assert stream["realitySettings"]["shortId"] == "1234abcd"


def test_generate_trojan_websocket_config():
    link = "trojan://password123@trojan.net:443?type=ws&security=tls&path=%2Fws&host=trojan.net#TrojanWS"
    cfg = parse_trojan(link)
    xray_json = generate_test_xray_config(cfg, socks_port=10809)

    proxy_out = xray_json["outbounds"][0]
    assert proxy_out["protocol"] == "trojan"
    assert proxy_out["settings"]["servers"][0]["password"] == "password123"

    stream = proxy_out["streamSettings"]
    assert stream["network"] == "ws"
    assert stream["security"] == "tls"
    assert stream["wsSettings"]["path"] == "/ws"
    assert stream["wsSettings"]["headers"]["Host"] == "trojan.net"


def test_generate_invalid_port():
    link = "trojan://pass@host:443#Test"
    cfg = parse_trojan(link)
    with pytest.raises(ValueError, match="Invalid socks port"):
        generate_test_xray_config(cfg, socks_port=80)
