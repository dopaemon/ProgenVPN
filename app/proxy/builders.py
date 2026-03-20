#!/usr/bin/env python
import base64
import json
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote

from app.proxy.models import ProxyContext, ProxyRequest


def build_stream_settings(request: ProxyRequest) -> dict[str, Any]:
    stream_settings: dict[str, Any] = {
        "network": request.network,
        "security": request.security,
    }

    if request.network == "ws":
        stream_settings["wsSettings"] = {
            "path": request.path or "/",
            "headers": {"Host": request.host} if request.host else {},
        }
    elif request.network == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": (request.path or "/").lstrip("/"),
            "authority": request.host,
        }
    else:
        stream_settings["tcpSettings"] = {"header": {"type": request.header_type}}

    if request.security in {"tls", "reality"}:
        stream_settings["tlsSettings"] = {
            "serverName": request.sni or request.address,
            "fingerprint": request.fingerprint or "chrome",
            "alpn": [item.strip() for item in request.alpn.split(",") if item.strip()],
        }

    return stream_settings


class ShareLinkBuilder(ABC):
    def __init__(self, context: ProxyContext) -> None:
        self.context = context

    @property
    def request(self):
        return self.context.request

    @property
    def node(self):
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
            "add": self.request.address,
            "port": str(self.node.port),
            "id": self.node.uuid,
            "aid": str(self.node.alter_id),
            "scy": "auto",
            "net": self.request.network,
            "type": self.request.header_type,
            "host": self.request.host,
            "path": self.request.path,
            "tls": "" if self.request.security == "none" else self.request.security,
            "sni": self.request.sni,
            "alpn": self.request.alpn,
            "fp": self.request.fingerprint,
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
                        "address": self.request.address,
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
            "streamSettings": build_stream_settings(self.request),
        }


class VlessShareLinkBuilder(ShareLinkBuilder):
    def build_share_link(self) -> str:
        query_parts = [
            ("encryption", "none"),
            ("security", self.request.security),
            ("type", self.request.network),
            ("headerType", self.request.header_type),
        ]
        if self.request.host:
            query_parts.append(("host", self.request.host))
        if self.request.path and self.request.network in {"ws", "grpc"}:
            query_parts.append(("path", self.request.path))
        if self.request.sni:
            query_parts.append(("sni", self.request.sni))
        if self.request.fingerprint and self.request.security in {"tls", "reality"}:
            query_parts.append(("fp", self.request.fingerprint))
        if self.request.alpn:
            query_parts.append(("alpn", self.request.alpn))
        if self.request.flow:
            query_parts.append(("flow", self.request.flow))

        query = "&".join(
            f"{quote(key, safe='')}={quote(value, safe='/:,')}"
            for key, value in query_parts
            if value not in {"", "none"} or key in {"encryption", "security", "type"}
        )
        label = quote(self.node.remark, safe="")
        return (
            f"vless://{self.node.uuid}@{self.request.address}:{self.node.port}"
            f"?{query}#{label}"
        )

    def build_import_payload(self) -> dict[str, Any]:
        return {
            "protocol": "vless",
            "tag": self.node.remark,
            "settings": {
                "vnext": [
                    {
                        "address": self.request.address,
                        "port": self.node.port,
                        "users": [
                            {
                                "id": self.node.uuid,
                                "encryption": "none",
                                "flow": self.request.flow,
                            }
                        ],
                    }
                ]
            },
            "streamSettings": build_stream_settings(self.request),
        }


def resolve_builder(context: ProxyContext) -> ShareLinkBuilder:
    if context.request.protocol == "vmess":
        return VmessShareLinkBuilder(context)
    return VlessShareLinkBuilder(context)
