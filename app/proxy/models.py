#!/usr/bin/env python
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.proxy.utils import clean_text


@dataclass
class ProxyNode:
    remark: str
    port: int
    uuid: str
    alter_id: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any], index: int) -> "ProxyNode":
        node = cls(
            remark=clean_text(payload.get("remark"), f"Node {index}"),
            port=int(clean_text(payload.get("port"), "443")),
            uuid=clean_text(payload.get("uuid")),
            alter_id=int(clean_text(payload.get("alter_id"), "0")),
        )
        node.validate()
        return node

    def validate(self) -> None:
        if not self.remark:
            raise ValueError("Remark cua node la bat buoc.")
        if not 1 <= self.port <= 65535:
            raise ValueError("Port cua node phai nam trong khoang 1-65535.")
        UUID(self.uuid)


@dataclass
class ProxyRequest:
    protocol: str
    address: str
    network: str
    security: str
    host: str
    path: str
    sni: str
    fingerprint: str
    alpn: str
    flow: str
    header_type: str
    nodes: list[ProxyNode]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ProxyRequest":
        raw_nodes = payload.get("nodes") or []
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ValueError("Can it nhat mot node de tao proxy.")

        request_data = cls(
            protocol=clean_text(payload.get("protocol"), "vmess").lower(),
            address=clean_text(payload.get("address"), "server.example.com"),
            network=clean_text(payload.get("network"), "ws").lower(),
            security=clean_text(payload.get("security"), "tls").lower(),
            host=clean_text(payload.get("host")),
            path=clean_text(payload.get("path"), "/"),
            sni=clean_text(payload.get("sni")),
            fingerprint=clean_text(payload.get("fingerprint"), "chrome").lower(),
            alpn=clean_text(payload.get("alpn")),
            flow=clean_text(payload.get("flow")),
            header_type=clean_text(payload.get("header_type"), "none"),
            nodes=[
                ProxyNode.from_dict(item, index)
                for index, item in enumerate(raw_nodes, start=1)
            ],
        )
        request_data.validate()
        return request_data

    def validate(self) -> None:
        if self.protocol not in {"vmess", "vless"}:
            raise ValueError("Protocol chi ho tro VMess hoac VLESS.")
        if self.network not in {"tcp", "ws", "grpc"}:
            raise ValueError("Network chi ho tro tcp, ws hoac grpc.")
        if self.security not in {"none", "tls", "reality"}:
            raise ValueError("Security chi ho tro none, tls hoac reality.")
        if not self.address:
            raise ValueError("Server address la bat buoc.")


@dataclass
class ProxyContext:
    request: ProxyRequest
    node: ProxyNode
