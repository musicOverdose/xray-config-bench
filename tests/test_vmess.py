"""Unit tests for VMess share link parsing and validation."""

import base64
import json
import pytest
from app.config_parser.vmess import parse_vmess, safe_b64decode


def test_parse_vmess_standard_json():
    data = {
        "v": "2",
        "ps": "VMess Germany",
        "add": "de.example.com",
        "port": 443,
        "id": "e98e2170-c75c-4f8e-9c4f-9e73111f185c",
        "aid": 0,
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "cdn.example.com",
        "path": "/stream",
        "tls": "tls",
        "sni": "cdn.example.com",
        "alpn": "h2,http/1.1",
        "fp": "firefox",
    }
    raw_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    link = f"vmess://{raw_b64}"

    config = parse_vmess(link)
    assert config.protocol == "vmess"
    assert config.server == "de.example.com"
    assert config.port == 443
    assert config.uuid == "e98e2170-c75c-4f8e-9c4f-9e73111f185c"
    assert config.alter_id == 0
    assert config.cipher == "auto"
    assert config.network == "ws"
    assert config.ws_path == "/stream"
    assert config.ws_headers.get("Host") == "cdn.example.com"
    assert config.security == "tls"
    assert config.sni == "cdn.example.com"
    assert config.fingerprint == "firefox"
    assert config.name == "VMess Germany"
    assert "h2" in config.alpn


def test_parse_vmess_unpadded_base64():
    data = {
        "v": "2",
        "ps": "Node Unpadded",
        "add": "1.1.1.1",
        "port": 80,
        "id": "11111111-2222-3333-4444-555555555555",
        "net": "tcp",
    }
    raw_b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8").rstrip("=")
    link = f"vmess://{raw_b64}"

    config = parse_vmess(link)
    assert config.server == "1.1.1.1"
    assert config.name == "Node Unpadded"


def test_parse_vmess_malformed():
    with pytest.raises(ValueError, match="Failed to decode VMess"):
        parse_vmess("vmess://!!!corrupt_base64!!!")

    bad_data = {"v": "2", "ps": "No Host", "port": 443, "id": "uuid"}
    b64 = base64.b64encode(json.dumps(bad_data).encode("utf-8")).decode("utf-8")
    with pytest.raises(ValueError, match="missing server address"):
        parse_vmess(f"vmess://{b64}")
