# Xray (VLESS + WebSocket) on DeployVera — free plan
#
# Base: Alpine + official Xray-core release binary.
# TLS is terminated by DeployVera's edge proxy, so Xray itself listens
# plain (security: none) on $PORT and speaks WebSocket only.
# The container runs as an unprivileged user and writes nothing to the
# image filesystem at runtime: the generated config goes to /tmp.
#
# Xray version pinned to the newest upstream release verified 2026-11-22:
# v26.10.31 (https://github.com/XTLS/Xray-core/releases/tag/v26.10.31).
# If the build 404s on the download, bump XRAY_VERSION to the newest tag
# at https://github.com/XTLS/Xray-core/releases (date-stamped tags).

FROM alpine:3.21

ARG XRAY_VERSION=26.10.31

RUN apk add --no-cache ca-certificates curl python3 unzip \
 && mkdir -p /usr/local/bin /etc/xray /tmp/xray \
 && curl -fsSL -o /tmp/xray.zip \
      "https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip" \
 && unzip -o /tmp/xray.zip -d /tmp/xray \
 && install -m 0755 /tmp/xray/xray /usr/local/bin/xray \
 && rm -rf /tmp/xray.zip /tmp/xray \
 && /usr/local/bin/xray version \
 && adduser -D -H -s /sbin/nologin xray

WORKDIR /app
COPY gen-config.py http-front.py entrypoint.sh ./
COPY config.example.json ./

# Xray only needs to read its files; the generated live config lives in /tmp.
RUN chmod 0755 entrypoint.sh \
 && chmod 0644 gen-config.py http-front.py config.example.json \
 && chown -R xray:xray /app

USER xray

# Env vars (set in the DeployVera panel; never commit real values):
#   UUID        (required) VLESS client UUID, e.g. uuidgen output
#   WS_PATH     (optional, default /vless) WebSocket path, must start with /
#   PORT        (set by the platform) public-facing listen port
#   FRONT_PROXY (optional, default 1) 1 = tiny HTTP front proxy on $PORT
#               (answers health checks with 200, forwards WS upgrades to
#               Xray on 127.0.0.1:10000); 0 = Xray listens directly on $PORT
#   LOGLEVEL    (optional, default warning) Xray log level
ENV WS_PATH=/vless \
    FRONT_PROXY=1 \
    LOGLEVEL=warning

EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
