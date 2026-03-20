#!/usr/bin/env python

DEFAULT_PROXY_VALUES = {
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
}

DEFAULT_NODE_VALUES = {
    "remark": "Node 1",
    "port": 443,
    "alter_id": 0,
}
