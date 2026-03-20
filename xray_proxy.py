#!/usr/bin/env python
import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from uuid import UUID


def _clean(value: str, fallback: str = "") -> str:
    return (value or fallback).strip()


@dataclass
class ProxyFormData:
    protocol: str
    remark: str
    address: str
    port: int
    uuid: str
    network: str
    security: str
    host: str
    path: str
    sni: str
    fingerprint: str
    alpn: str
    flow: str
    alter_id: int
    header_type: str

    @classmethod
    def from_form(cls, form: Any) -> "ProxyFormData":
        protocol = _clean(form.get("protocol"), "vmess").lower()
        network = _clean(form.get("network"), "ws").lower()
        security = _clean(form.get("security"), "tls").lower()
        fingerprint = _clean(form.get("fingerprint"), "chrome").lower()

        data = cls(
            protocol=protocol,
            remark=_clean(form.get("remark"), "Personal Xray"),
            address=_clean(form.get("address"), "example.com"),
            port=int(_clean(form.get("port"), "443")),
            uuid=_clean(form.get("uuid"), "00000000-0000-0000-0000-000000000000"),
            network=network,
            security=security,
            host=_clean(form.get("host")),
            path=_clean(form.get("path"), "/"),
            sni=_clean(form.get("sni")),
            fingerprint=fingerprint,
            alpn=_clean(form.get("alpn")),
            flow=_clean(form.get("flow")),
            alter_id=int(_clean(form.get("alter_id"), "0")),
            header_type=_clean(form.get("header_type"), "none"),
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
        if not 1 <= self.port <= 65535:
            raise ValueError("Port phai nam trong khoang 1-65535.")
        UUID(self.uuid)


class ShareLinkBuilder(ABC):
    def __init__(self, data: ProxyFormData) -> None:
        self.data = data

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
            "ps": self.data.remark,
            "add": self.data.address,
            "port": str(self.data.port),
            "id": self.data.uuid,
            "aid": str(self.data.alter_id),
            "scy": "auto",
            "net": self.data.network,
            "type": self.data.header_type,
            "host": self.data.host,
            "path": self.data.path,
            "tls": "" if self.data.security == "none" else self.data.security,
            "sni": self.data.sni,
            "alpn": self.data.alpn,
            "fp": self.data.fingerprint,
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")
        return f"vmess://{encoded}"

    def build_import_payload(self) -> dict[str, Any]:
        return {
            "protocol": "vmess",
            "tag": self.data.remark,
            "settings": {
                "vnext": [
                    {
                        "address": self.data.address,
                        "port": self.data.port,
                        "users": [
                            {
                                "id": self.data.uuid,
                                "alterId": self.data.alter_id,
                                "security": "auto",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": _stream_settings(self.data),
        }


class VlessShareLinkBuilder(ShareLinkBuilder):
    def build_share_link(self) -> str:
        query_parts = [
            ("encryption", "none"),
            ("security", self.data.security),
            ("type", self.data.network),
            ("headerType", self.data.header_type),
        ]
        if self.data.host:
            query_parts.append(("host", self.data.host))
        if self.data.path and self.data.network in {"ws", "grpc"}:
            query_parts.append(("path", self.data.path))
        if self.data.sni:
            query_parts.append(("sni", self.data.sni))
        if self.data.fingerprint and self.data.security in {"tls", "reality"}:
            query_parts.append(("fp", self.data.fingerprint))
        if self.data.alpn:
            query_parts.append(("alpn", self.data.alpn))
        if self.data.flow:
            query_parts.append(("flow", self.data.flow))

        query = "&".join(
            f"{quote(key, safe='')}={quote(value, safe='/:,')}"
            for key, value in query_parts
            if value not in {"", "none"} or key in {"encryption", "security", "type"}
        )
        label = quote(self.data.remark, safe="")
        return f"vless://{self.data.uuid}@{self.data.address}:{self.data.port}?{query}#{label}"

    def build_import_payload(self) -> dict[str, Any]:
        return {
            "protocol": "vless",
            "tag": self.data.remark,
            "settings": {
                "vnext": [
                    {
                        "address": self.data.address,
                        "port": self.data.port,
                        "users": [
                            {
                                "id": self.data.uuid,
                                "encryption": "none",
                                "flow": self.data.flow,
                            }
                        ],
                    }
                ]
            },
            "streamSettings": _stream_settings(self.data),
        }


def _stream_settings(data: ProxyFormData) -> dict[str, Any]:
    stream_settings: dict[str, Any] = {
        "network": data.network,
        "security": data.security,
    }

    if data.network == "ws":
        stream_settings["wsSettings"] = {
            "path": data.path or "/",
            "headers": {"Host": data.host} if data.host else {},
        }
    elif data.network == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": (data.path or "/").lstrip("/"),
            "authority": data.host,
        }
    else:
        stream_settings["tcpSettings"] = {"header": {"type": data.header_type}}

    if data.security in {"tls", "reality"}:
        stream_settings["tlsSettings"] = {
            "serverName": data.sni or data.address,
            "fingerprint": data.fingerprint or "chrome",
            "alpn": [item.strip() for item in data.alpn.split(",") if item.strip()],
        }

    return stream_settings


class QRCodeService:
    @staticmethod
    def build_image_url(content: str, size: int = 280) -> str:
        return (
            "https://quickchart.io/qr"
            f"?size={size}&margin=2&text={quote(content, safe='')}"
        )


class ProxyShareService:
    def __init__(self, data: ProxyFormData) -> None:
        self.data = data
        self.builder = self._resolve_builder()

    def _resolve_builder(self) -> ShareLinkBuilder:
        if self.data.protocol == "vmess":
            return VmessShareLinkBuilder(self.data)
        return VlessShareLinkBuilder(self.data)

    def build(self) -> dict[str, Any]:
        share_link = self.builder.build_share_link()
        return {
            "share_link": share_link,
            "qr_code_url": QRCodeService.build_image_url(share_link),
            "payload_json": json.dumps(
                self.builder.build_import_payload(),
                ensure_ascii=False,
                indent=2,
            ),
        }
