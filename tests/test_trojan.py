"""Unit tests for Trojan share link parsing and validation."""

import pytest
from app.config_parser.trojan import parse_trojan


def test_parse_trojan_tls():
    link = "trojan://secret_pass_123@trojan.example.com:443?security=tls&sni=trojan.example.com&alpn=h2#Trojan%20Fast"
    config = parse_trojan(link)
    assert config.protocol == "trojan"
    assert config.server == "trojan.example.com"
    assert config.port == 443
    assert config.password == "secret_pass_123"
    assert config.security == "tls"
    assert config.sni == "trojan.example.com"
    assert "h2" in config.alpn
    assert config.name == "Trojan Fast"


def test_parse_trojan_grpc():
    link = "trojan://password@grpc.example.com:443?type=grpc&serviceName=my-grpc-service&mode=multi#Trojan%20gRPC"
    config = parse_trojan(link)
    assert config.network == "grpc"
    assert config.grpc_service_name == "my-grpc-service"
    assert config.grpc_mode == "multi"
    assert config.name == "Trojan gRPC"


def test_parse_trojan_malformed():
    with pytest.raises(ValueError, match="missing '@'"):
        parse_trojan("trojan://no_at_symbol_here")

    with pytest.raises(ValueError, match="missing a password"):
        parse_trojan("trojan://@host.com:443")

    with pytest.raises(ValueError, match="Invalid port"):
        parse_trojan("trojan://pass@host.com:not_a_port")
