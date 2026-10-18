"""Data models for parsed V2Ray/Xray configurations."""

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional


@dataclass
class ProxyConfig:
    protocol: str  # 'vless', 'vmess', 'trojan', 'shadowsocks'
    server: str
    port: int
    name: str = ""
    uuid: str = ""  # For vless / vmess
    password: str = ""  # For trojan / shadowsocks
    alter_id: int = 0  # For vmess
    cipher: str = ""  # For shadowsocks / vmess
    network: str = "tcp"  # tcp, ws, grpc, http, kcp
    security: str = "none"  # none, tls, reality
    sni: str = ""
    alpn: List[str] = field(default_factory=list)
    fingerprint: str = ""  # chrome, firefox, etc.
    flow: str = ""  # xtls-rprx-vision
    public_key: str = ""  # Reality pbk
    short_id: str = ""  # Reality sid
    spider_x: str = ""  # Reality spx
    ws_path: str = ""
    ws_headers: Dict[str, str] = field(default_factory=dict)
    grpc_service_name: str = ""
    grpc_mode: str = "gun"
    raw_link: str = ""
    source_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    unique_hash: str = ""

    def __post_init__(self):
        if not self.unique_hash:
            self.unique_hash = self.compute_hash()
        if not self.name:
            self.name = f"{self.protocol.upper()} - {self.server}:{self.port}"

    def compute_hash(self) -> str:
        """
        Compute a deterministic hash based on connection-defining parameters.
        Two configurations with the same server, port, credentials, transport,
        and TLS settings are considered duplicates even if their remarks differ.
        """
        ident = (
            f"{self.protocol.lower()}|{self.server.strip().lower()}|{self.port}|"
            f"{self.uuid.strip()}|{self.password.strip()}|{self.cipher.strip().lower()}|"
            f"{self.network.strip().lower()}|{self.security.strip().lower()}|"
            f"{self.sni.strip().lower()}|{self.ws_path.strip()}|{self.grpc_service_name.strip()}|"
            f"{self.public_key.strip()}"
        )
        return hashlib.sha256(ident.encode("utf-8")).hexdigest()

    @property
    def display_name(self) -> str:
        return self.name.strip() if self.name else f"{self.server}:{self.port}"

    def safe_summary(self) -> str:
        """Return a credential-free summary of configuration attributes."""
        sec_desc = self.security
        if self.security == "reality":
            sec_desc = "reality" + (f"({self.sni})" if self.sni else "")
        elif self.security == "tls" and self.sni:
            sec_desc = f"tls({self.sni})"

        transport_desc = self.network
        if self.network == "ws" and self.ws_path:
            transport_desc = f"ws({self.ws_path})"
        elif self.network == "grpc" and self.grpc_service_name:
            transport_desc = f"grpc({self.grpc_service_name})"

        return f"[{self.protocol.upper()}] {self.server}:{self.port} ({transport_desc}/{sec_desc})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "server": self.server,
            "port": self.port,
            "name": self.name,
            "uuid": self.uuid,
            "password": self.password,
            "alter_id": self.alter_id,
            "cipher": self.cipher,
            "network": self.network,
            "security": self.security,
            "sni": self.sni,
            "alpn": self.alpn,
            "fingerprint": self.fingerprint,
            "flow": self.flow,
            "public_key": self.public_key,
            "short_id": self.short_id,
            "spider_x": self.spider_x,
            "ws_path": self.ws_path,
            "ws_headers": self.ws_headers,
            "grpc_service_name": self.grpc_service_name,
            "grpc_mode": self.grpc_mode,
            "raw_link": self.raw_link,
            "source_id": self.source_id,
            "extra": self.extra,
            "unique_hash": self.unique_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxyConfig":
        data_copy = dict(data)
        if isinstance(data_copy.get("alpn"), str):
            try:
                data_copy["alpn"] = json.loads(data_copy["alpn"])
            except Exception:
                data_copy["alpn"] = [s.strip() for s in data_copy["alpn"].split(",") if s.strip()]
        if isinstance(data_copy.get("ws_headers"), str):
            try:
                data_copy["ws_headers"] = json.loads(data_copy["ws_headers"])
            except Exception:
                data_copy["ws_headers"] = {}
        if isinstance(data_copy.get("extra"), str):
            try:
                data_copy["extra"] = json.loads(data_copy["extra"])
            except Exception:
                data_copy["extra"] = {}
        return cls(**data_copy)
