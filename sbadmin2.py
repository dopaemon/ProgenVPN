#!/usr/bin/env python
import jinja2.exceptions
from flask import Flask, jsonify, render_template, request

from xray_proxy import ProxyBatchFormData, ProxyShareService, UUIDService

app = Flask(__name__)


DEFAULT_PROXY_FORM = {
    "protocol": "vmess",
    "address": "server.example.com",
    "network": "ws",
    "security": "tls",
    "host": "server.example.com",
    "path": "/ray",
    "sni": "server.example.com",
    "fingerprint": "chrome",
    "alpn": "h2,http/1.1",
    "flow": "",
    "header_type": "none",
    "nodes": [
        {
            "remark": "Node 1",
            "port": 443,
            "uuid": UUIDService.generate(),
            "alter_id": 0,
        }
    ],
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/proxy')
def proxy():
    return render_template('proxy.html', form_data=DEFAULT_PROXY_FORM)


@app.route('/api/proxy/uuid')
def proxy_uuid():
    return jsonify({"uuid": UUIDService.generate()})


@app.route('/api/proxy/build', methods=['POST'])
def proxy_build():
    payload = request.get_json(silent=True) or {}
    try:
        data = ProxyBatchFormData.from_payload(payload)
        result = ProxyShareService(data).build()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route('/<pagename>')
def admin(pagename):
    return render_template(pagename + '.html')


@app.errorhandler(jinja2.exceptions.TemplateNotFound)
def template_not_found(error):
    return not_found(error)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
