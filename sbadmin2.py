#!/usr/bin/env python
from flask import Flask, render_template, request
import jinja2.exceptions

from xray_proxy import ProxyFormData, ProxyShareService

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    context = {
        "form_data": {
            "protocol": "vmess",
            "remark": "Personal Xray",
            "address": "server.example.com",
            "port": 443,
            "uuid": "11111111-1111-1111-1111-111111111111",
            "network": "ws",
            "security": "tls",
            "host": "server.example.com",
            "path": "/ray",
            "sni": "server.example.com",
            "fingerprint": "chrome",
            "alpn": "h2,http/1.1",
            "flow": "",
            "alter_id": 0,
            "header_type": "none",
        },
        "result": None,
        "error": None,
    }

    if request.method == 'POST':
        context["form_data"] = request.form.to_dict()
        try:
            data = ProxyFormData.from_form(request.form)
            context["result"] = ProxyShareService(data).build()
        except ValueError as exc:
            context["error"] = str(exc)

    return render_template('proxy.html', **context)


@app.route('/<pagename>')
def admin(pagename):
    return render_template(pagename+'.html')


@app.errorhandler(jinja2.exceptions.TemplateNotFound)
def template_not_found(e):
    return not_found(e)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
