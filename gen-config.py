#!/usr/bin/env python3
"""Render /tmp/xray-config.json from environment variables.

Env vars:
  UUID        (required) VLESS client UUID
  WS_PATH     (default /vless) WebSocket path, must start with /
  PORT        (required) platform-assigned port; used as Xray's listen
              port when FRONT_PROXY=0, ignored for the listen port when
              FRONT_PROXY=1 (Xray then binds 127.0.0.1:10000)
  FRONT_PROXY (default 1)
  LOGLEVEL    (default warning)
"""
import json
import os
import sys

uuid = os.environ.get("UUID", "").strip()
if not uuid:
    sys.exit("gen-config.py: UUID env var is required")

ws_path = os.environ.get("WS_PATH", "/vless").strip() or "/vless"
if not ws_path.startswith("/"):
    ws_path = "/" + ws_path

port = int(os.environ.get("PORT", "8080"))
front_proxy = os.environ.get("FRONT_PROXY", "1") == "1"
loglevel = os.environ.get("LOGLEVEL", "warning").strip() or "warning"

if front_proxy:
    listen_addr = "127.0.0.1"
    listen_port = 10000
else:
    listen_addr = "0.0.0.0"
    listen_port = port

config = {
    "log": {"loglevel": loglevel},
    "inbounds": [
        {
            "port": listen_port,
            "listen": listen_addr,
            "protocol": "vless",
            "settings": {
                "clients": [{"id": uuid, "flow": ""}],
                "decryption": "none",
            },
            "streamSettings": {
                "network": "ws",
                "security": "none",
                "wsSettings": {"path": ws_path},
            },
            "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
        }
    ],
    "outbounds": [
        {"protocol": "freedom", "tag": "direct"},
        {"protocol": "blackhole", "tag": "blocked"},
    ],
}

with open("/tmp/xray-config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)

print(
    "wrote /tmp/xray-config.json "
    f"(listen {listen_addr}:{listen_port}, ws path {ws_path}, "
    f"front_proxy={'on' if front_proxy else 'off'})"
)
