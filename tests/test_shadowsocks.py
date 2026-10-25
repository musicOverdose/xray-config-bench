"""Unit tests for Shadowsocks share link parsing."""

import base64
import pytest
from app.config_parser.shadowsocks import parse_shadowsocks


def test_parse_shadowsocks_sip002():
    # SIP002: ss://base64(method:password)@host:port#remark
    userinfo = base64.b64encode(b"aes-256-gcm:pass1234").decode("utf-8")
    link = f"ss://{userinfo}@ss.example.com:8388#Shadowsocks%20Node"

    config = parse_shadowsocks(link)
    assert config.protocol == "shadowsocks"
    assert config.server == "ss.example.com"
    assert config.port == 8388
    assert config.cipher == "aes-256-gcm"
    assert config.password == "pass1234"
    assert config.name == "Shadowsocks Node"


def test_parse_shadowsocks_legacy():
    # Legacy: ss://base64(method:password@host:port)#remark
    payload = base64.b64encode(b"chacha20-ietf-poly1305:mysecret@legacy.node:9000").decode("utf-8")
    link = f"ss://{payload}#Legacy%20SS"

    config = parse_shadowsocks(link)
    assert config.protocol == "shadowsocks"
    assert config.server == "legacy.node"
    assert config.port == 9000
    assert config.cipher == "chacha20-ietf-poly1305"
    assert config.password == "mysecret"
    assert config.name == "Legacy SS"


def test_parse_shadowsocks_malformed():
    with pytest.raises(ValueError):
        parse_shadowsocks("ss://not_a_valid_ss_link")
