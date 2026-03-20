#!/usr/bin/env python
import base64
import json
import subprocess
from io import BytesIO
from uuid import uuid4

try:
    import qrcode
except ImportError:  # pragma: no cover - depends on environment packages
    qrcode = None

from app.proxy.builders import resolve_builder
from app.proxy.constants import DEFAULT_NODE_VALUES, DEFAULT_PROXY_VALUES
from app.proxy.models import ProxyContext, ProxyRequest


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


class ProxyFormService:
    @staticmethod
    def build_defaults() -> dict[str, object]:
        default_node = dict(DEFAULT_NODE_VALUES)
        default_node["uuid"] = UUIDService.generate()

        defaults = dict(DEFAULT_PROXY_VALUES)
        defaults["nodes"] = [default_node]
        return defaults


class ProxyShareService:
    def __init__(self, request_data: ProxyRequest) -> None:
        self.request_data = request_data

    def build(self) -> dict[str, object]:
        results = []
        for node in self.request_data.nodes:
            context = ProxyContext(request=self.request_data, node=node)
            builder = resolve_builder(context)
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
            "protocol": self.request_data.protocol,
            "address": self.request_data.address,
            "node_count": len(results),
            "results": results,
        }
