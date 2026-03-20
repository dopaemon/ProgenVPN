#!/usr/bin/env python
import base64
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

try:
    import qrcode
except ImportError:  # pragma: no cover - depends on environment packages
    qrcode = None


def _clean(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


@dataclass
class ProxyNodeFormData:
    remark: str
    port: int
    uuid: str
    alter_id: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any], index: int) -> "ProxyNodeFormData":
        node = cls(
            remark=_clean(payload.get("remark"), f"Node {index}"),
            port=int(_clean(payload.get("port"), "443")),
            uuid=_clean(payload.get("uuid")),
            alter_id=int(_clean(payload.get("alter_id"), "0")),
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
class ProxyBatchFormData:
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
    nodes: list[ProxyNodeFormData]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ProxyBatchFormData":
        protocol = _clean(payload.get("protocol"), "vmess").lower()
        network = _clean(payload.get("network"), "ws").lower()
        security = _clean(payload.get("security"), "tls").lower()
        fingerprint = _clean(payload.get("fingerprint"), "chrome").lower()
        raw_nodes = payload.get("nodes") or []
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ValueError("Can it nhat mot node de tao proxy.")

        data = cls(
            protocol=protocol,
            address=_clean(payload.get("address"), "server.example.com"),
            network=network,
            security=security,
            host=_clean(payload.get("host")),
            path=_clean(payload.get("path"), "/"),
            sni=_clean(payload.get("sni")),
            fingerprint=fingerprint,
            alpn=_clean(payload.get("alpn")),
            flow=_clean(payload.get("flow")),
            header_type=_clean(payload.get("header_type"), "none"),
            nodes=[
                ProxyNodeFormData.from_dict(item, index)
                for index, item in enumerate(raw_nodes, start=1)
            ],
        )
        data.validate()
        return data

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
class ProxyNodeContext:
    batch: ProxyBatchFormData
    node: ProxyNodeFormData


class ShareLinkBuilder(ABC):
    def __init__(self, context: ProxyNodeContext) -> None:
        self.context = context

    @property
    def batch(self) -> ProxyBatchFormData:
        return self.context.batch

    @property
    def node(self) -> ProxyNodeFormData:
        return self.context.node

    @abstractmethod
    def build_share_link(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_import_payload(self) -> dict[str, Any]:
        raise NotImplementedError


class VmessShareLinkBuilder(ShareLinkBuilder):
    def build_share_link(self) -> str:
        payload = {
            "v": "2",
            "ps": self.node.remark,
            "add": self.batch.address,
            "port": str(self.node.port),
            "id": self.node.uuid,
            "aid": str(self.node.alter_id),
            "scy": "auto",
            "net": self.batch.network,
            "type": self.batch.header_type,
            "host": self.batch.host,
            "path": self.batch.path,
            "tls": "" if self.batch.security == "none" else self.batch.security,
            "sni": self.batch.sni,
            "alpn": self.batch.alpn,
            "fp": self.batch.fingerprint,
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")
        return f"vmess://{encoded}"

    def build_import_payload(self) -> dict[str, Any]:
        return {
            "protocol": "vmess",
            "tag": self.node.remark,
            "settings": {
                "vnext": [
                    {
                        "address": self.batch.address,
                        "port": self.node.port,
                        "users": [
                            {
                                "id": self.node.uuid,
                                "alterId": self.node.alter_id,
                                "security": "auto",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": _stream_settings(self.batch),
        }


class VlessShareLinkBuilder(ShareLinkBuilder):
    def build_share_link(self) -> str:
        query_parts = [
            ("encryption", "none"),
            ("security", self.batch.security),
            ("type", self.batch.network),
            ("headerType", self.batch.header_type),
        ]
        if self.batch.host:
            query_parts.append(("host", self.batch.host))
        if self.batch.path and self.batch.network in {"ws", "grpc"}:
            query_parts.append(("path", self.batch.path))
        if self.batch.sni:
            query_parts.append(("sni", self.batch.sni))
        if self.batch.fingerprint and self.batch.security in {"tls", "reality"}:
            query_parts.append(("fp", self.batch.fingerprint))
        if self.batch.alpn:
            query_parts.append(("alpn", self.batch.alpn))
        if self.batch.flow:
            query_parts.append(("flow", self.batch.flow))

        query = "&".join(
            f"{quote(key, safe='')}={quote(value, safe='/:,')}"
            for key, value in query_parts
            if value not in {"", "none"} or key in {"encryption", "security", "type"}
        )
        label = quote(self.node.remark, safe="")
        return (
            f"vless://{self.node.uuid}@{self.batch.address}:{self.node.port}"
            f"?{query}#{label}"
        )

    def build_import_payload(self) -> dict[str, Any]:
        return {
            "protocol": "vless",
            "tag": self.node.remark,
            "settings": {
                "vnext": [
                    {
                        "address": self.batch.address,
                        "port": self.node.port,
                        "users": [
                            {
                                "id": self.node.uuid,
                                "encryption": "none",
                                "flow": self.batch.flow,
                            }
                        ],
                    }
                ]
            },
            "streamSettings": _stream_settings(self.batch),
        }


def _stream_settings(batch: ProxyBatchFormData) -> dict[str, Any]:
    stream_settings: dict[str, Any] = {
        "network": batch.network,
        "security": batch.security,
    }

    if batch.network == "ws":
        stream_settings["wsSettings"] = {
            "path": batch.path or "/",
            "headers": {"Host": batch.host} if batch.host else {},
        }
    elif batch.network == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": (batch.path or "/").lstrip("/"),
            "authority": batch.host,
        }
    else:
        stream_settings["tcpSettings"] = {"header": {"type": batch.header_type}}

    if batch.security in {"tls", "reality"}:
        stream_settings["tlsSettings"] = {
            "serverName": batch.sni or batch.address,
            "fingerprint": batch.fingerprint or "chrome",
            "alpn": [item.strip() for item in batch.alpn.split(",") if item.strip()],
        }

    return stream_settings


class UUIDService:
    @staticmethod
    def generate() -> str:
        try:
            completed = subprocess.run(
                ["uuidgen"],
                check=True,
                capture_output=True,
                text=True,
            )
            return completed.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return str(uuid4())


class QRCodeService:
    @staticmethod
    def build_data_uri(content: str) -> str:
        if qrcode is None:
            raise ValueError("Thieu thu vien qrcode. Hay cai dat requirements Python truoc.")
        image = qrcode.make(content)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"


class ProxyShareService:
    def __init__(self, batch: ProxyBatchFormData) -> None:
        self.batch = batch

    def _resolve_builder(self, node: ProxyNodeFormData) -> ShareLinkBuilder:
        context = ProxyNodeContext(batch=self.batch, node=node)
        if self.batch.protocol == "vmess":
            return VmessShareLinkBuilder(context)
        return VlessShareLinkBuilder(context)

    def build(self) -> dict[str, Any]:
        results = []
        for node in self.batch.nodes:
            builder = self._resolve_builder(node)
            share_link = builder.build_share_link()
            results.append(
                {
                    "remark": node.remark,
                    "port": node.port,
                    "uuid": node.uuid,
                    "share_link": share_link,
                    "qr_code_data_uri": QRCodeService.build_data_uri(share_link),
                    "payload_json": json.dumps(
                        builder.build_import_payload(),
                        ensure_ascii=False,
                        indent=2,
                    ),
                }
            )

        return {
            "protocol": self.batch.protocol,
            "address": self.batch.address,
            "node_count": len(results),
            "results": results,
        }
