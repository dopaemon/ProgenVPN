#!/usr/bin/env python
from flask import Blueprint, jsonify, render_template, request

from app.proxy.models import ProxyRequest
from app.proxy.services import ProxyFormService, ProxyShareService, UUIDService


proxy_blueprint = Blueprint("proxy", __name__)


@proxy_blueprint.get("/proxy")
def proxy_page():
    return render_template("proxy.html", form_data=ProxyFormService.build_defaults())


@proxy_blueprint.get("/api/proxy/uuid")
def proxy_uuid():
    return jsonify({"uuid": UUIDService.generate()})


@proxy_blueprint.post("/api/proxy/build")
def proxy_build():
    payload = request.get_json(silent=True) or {}
    try:
        request_data = ProxyRequest.from_payload(payload)
        result = ProxyShareService(request_data).build()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)
