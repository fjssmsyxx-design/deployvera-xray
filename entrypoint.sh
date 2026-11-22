#!/bin/sh
# Entrypoint: generate /tmp/xray-config.json from env vars, then start Xray.
# If FRONT_PROXY=1 (default), Xray listens on 127.0.0.1:10000 and the tiny
# Python front proxy listens on $PORT: it answers plain HTTP (health checks)
# with 200 and pipes WebSocket upgrades through to Xray untouched.
# If FRONT_PROXY=0, Xray listens directly on $PORT.
set -eu

: "${UUID:?UUID env var is required (VLESS client UUID)}"
: "${WS_PATH:=/vless}"
: "${PORT:?PORT env var is required (set by the platform)}"
: "${FRONT_PROXY:=1}"
: "${LOGLEVEL:=warning}"

export UUID WS_PATH PORT FRONT_PROXY LOGLEVEL

# Render the live config into /tmp (the image filesystem may be read-only
# on some platforms; /tmp is always writable).
python3 /app/gen-config.py

if [ "$FRONT_PROXY" = "1" ]; then
  echo "starting xray on 127.0.0.1:10000, front proxy on 0.0.0.0:${PORT} (ws path ${WS_PATH})"
  /usr/local/bin/xray run -c /tmp/xray-config.json &
  XRAY_PID=$!
  # Give Xray a moment to bind before the front proxy starts accepting.
  sleep 1
  exec python3 /app/http-front.py
else
  echo "starting xray directly on 0.0.0.0:${PORT} (ws path ${WS_PATH})"
  exec /usr/local/bin/xray run -c /tmp/xray-config.json
fi
