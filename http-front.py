#!/usr/bin/env python3
"""Tiny HTTP front proxy for Xray-on-PaaS.

Why it exists: PaaS health checks do a plain HTTP GET against the app
and expect a 2xx answer. Xray's WebSocket inbound answers non-WS requests
with 4xx, which can make the platform mark the app unhealthy and roll
the deploy back. This proxy:

  * listens on 0.0.0.0:$PORT,
  * answers any plain HTTP request with `200 ok` (health checks pass),
  * forwards a real WebSocket upgrade whose path matches $WS_PATH to
    Xray on 127.0.0.1:10000, byte-for-byte, then pipes both directions
    until either side closes.

It never inspects, logs, or alters proxied bytes. Only the request line
and headers are read to decide routing. Query strings on the WS path
(e.g. `?ed=2048` early-data) are ignored for matching but forwarded
unchanged, so Xray still sees them.
"""
import os
import select
import socket
import sys
import threading

LISTEN_PORT = int(os.environ.get("PORT", "8080"))
WS_PATH = os.environ.get("WS_PATH", "/vless").strip() or "/vless"
XRAY_HOST = "127.0.0.1"
XRAY_PORT = 10000
BUF = 65536


def pipe(src, dst, stop):
    try:
        while not stop.is_set():
            r, _, _ = select.select([src], [], [], 30)
            if not r:
                continue
            data = src.recv(BUF)
            if not data:
                break
            dst.sendall(data)
    except (OSError, ValueError):
        pass
    finally:
        stop.set()
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def read_headers(conn):
    """Read until end of HTTP headers. Returns (head_bytes, leftover)."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(BUF)
        if not chunk:
            return None, b""
        buf += chunk
        if len(buf) > 65536:  # absurd header, bail out
            return None, b""
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head + b"\r\n\r\n", rest


def handle(conn, addr):
    try:
        head, rest = read_headers(conn)
        if head is None:
            return
        lines = head.decode("iso-8859-1").split("\r\n")
        method, target, _version = lines[0].split(" ", 2)
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        path = target.split("?", 1)[0]
        is_ws = (
            method.upper() == "GET"
            and path == WS_PATH
            and headers.get("upgrade", "").lower() == "websocket"
            and "upgrade" in headers.get("connection", "").lower()
        )
        if not is_ws:
            body = b"ok\n"
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: "
                + str(len(body)).encode()
                + b"\r\nConnection: close\r\n\r\n"
                + body
            )
            return
        upstream = socket.create_connection((XRAY_HOST, XRAY_PORT), timeout=10)
        upstream.sendall(head + rest)
        stop = threading.Event()
        t = threading.Thread(target=pipe, args=(conn, upstream, stop), daemon=True)
        t.start()
        pipe(upstream, conn, stop)
        t.join(timeout=5)
        upstream.close()
    except (OSError, ValueError):
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LISTEN_PORT))
    srv.listen(128)
    print(
        f"front proxy listening on 0.0.0.0:{LISTEN_PORT}, "
        f"ws path {WS_PATH} -> {XRAY_HOST}:{XRAY_PORT}",
        flush=True,
    )
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
