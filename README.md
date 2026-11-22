# DeployVera — Xray VLESS+WS deployment package

Research date: 2026-11-22. Research only — nothing registered, deployed, or paid.

## 1. What the free plan is (verified from DeployVera's own pages)

- 1 app, 0.5 vCPU, 512 MB RAM, 2 GB NVMe. Permanent, no expiry, no idle
  sleep / scale-to-zero, no card, no automatic conversion to paid.
- Deploys from GitHub or GitLab (or a public HTTPS repo) with a Dockerfile
  or Nixpacks auto-build; redeploys on every push to the connected branch.
- App must listen on `0.0.0.0` on the port from the `PORT` env var.
  Secrets go in panel env vars, never in the Dockerfile.
- Public URL is a temporary DeployVera address, e.g.
  `https://<app>.deployvera.com` (example seen on the homepage:
  `shop-api.deployvera.com`). Custom domain can be attached in the panel.
- No transfer/bandwidth limit is stated for the free plan anywhere in the
  docs — unknown, not "unlimited".
- Sources: https://deployvera.com/en/free-docker-hosting,
  https://deployvera.com/docs/en/quickstart,
  https://deployvera.com/docs/en/overview, https://deployvera.com/

## 2. Signup flow (verified — register page read directly)

- Signup URL: https://deployvera.com/register?plan=container-free
- Fields: Full name, Email address, Password. Optional: Phone (SMS code),
  National ID ("Not required for the free plan"). Must accept Terms of
  Service, Privacy Policy, KVKK notice. Marketing-email opt-in optional.
- No card, no billing details for the free plan. Email verification is
  required ("a verified email is enough to sign up").
- Captcha: none visible in the fetched page text — NOT confirmed (the page
  is partly JS-rendered; a captcha may appear in the live browser).
- GitHub/GitLab connection happens inside the panel after signup (OAuth).

## 3. How deployment works

1. Push this package to a GitHub or GitLab repo (public repo works without
   connecting an account; private repo needs the panel OAuth connection).
2. In the panel: create app → choose repo + branch → build method
   "Dockerfile" → set the port (use 8080, matching `run.port` in this
   package; the platform injects the same value as `PORT`).
3. Set env vars in the panel: `UUID` (generate with `uuidgen`), `WS_PATH`
   (default `/vless`), `FRONT_PROXY` (default `1`), `LOGLEVEL` (`warning`).
4. Deploy, watch build logs, verify the app is Live at its
   `https://<app>.deployvera.com` address.

## 4. Can it be deployed WITHOUT a browser?

Mostly yes, after a one-time browser step. DeployVera runs a hosted MCP
server at https://mcp.deployvera.com/mcp (21 tools: `list_projects`,
`create_project`, `deploy`, `get_build`, `get_build_logs`,
`explain_build_failure`, `set_env_vars`, `rollback`, …).
- Auth: browser OAuth on first use, OR a personal token created in the
  panel (Settings > AI agent access, `dvp_...`, 30/90/365-day validity).
- Catch: `create_project` ALWAYS needs owner approval in the browser
  (deployvera.com/approve, password + 2FA, 10-minute expiry). Deploys of an
  existing project do not need approval unless the token is set to require it.
- There is no documented public REST API for apps (only the MCP server and
  a public plans catalog at https://api.deployvera.com/api/plans).
- Source: https://deployvera.com/docs/en/mcp

## 5. WebSocket passthrough — UNCONFIRMED (biggest technical risk)

- The word "WebSocket" appears NOWHERE in DeployVera's full documentation
  (checked the complete https://deployvera.com/llms-full.txt, 1840 lines).
- Apps sit behind an "application proxy". Whether that proxy forwards the
  `Upgrade: websocket` handshake to the container is undocumented.
- The package is built to survive either way as far as possible (see §8),
  but a live test is the only way to know: if the proxy strips/breaks the
  upgrade, VLESS+WS cannot work on this platform and XHTTP would be the
  next thing to try (also undocumented).

## 6. Outbound network — NOT documented, assumed open

- No egress restrictions, blocked ports/protocols, or egress limits are
  stated anywhere in the docs. Builds fetch GitHub/GitLab; apps are
  expected to call external APIs/databases. Treat "container can reach the
  internet" as plausible but UNVERIFIED — the first deploy's Xray outbound
  test (step 9 below) is the proof.

## 7. Terms / AUP — NO explicit proxy/VPN ban found in the ToS

- Terms: https://deployvera.com/legal/terms-of-service (English translation
  of the Turkish original, which is binding). It requires compliance with
  "applicable law, third-party rights and the Acceptable Use Policy" and
  allows suspension for "unlawful content, use that threatens system
  security or failure to meet payment obligations". It does NOT name
  proxies, VPNs, tunnels, or Xray anywhere in the fetched text.
- ⚠️ The separate Acceptable Use Policy referenced by the ToS could NOT be
  retrieved: it is not indexed by search and its URL was not exposed in any
  fetched page. Its text is UNKNOWN — read it in the browser before
  deploying. A proxy/VPN ban may exist there.
- Operator: Yusuf Celal Çelik Bilişim ve İnternet Hizmetleri, Ankara,
  Türkiye. Turkish law applies; Antalya courts have jurisdiction. Prices
  are listed in TRY.
- Per the user's standing rule, a paper terms ban is a sorting reference,
  not a deployment veto — but here even the paper position is incomplete
  until the AUP is read.

## 8. Region — NOT officially stated; almost certainly Turkey / EU

- No region list or region picker appears in the docs. A third-party MCP
  listing describes DeployVera as having "servers in Turkey and the EU"
  (https://www.mcptop.com/server/deployvera). The company is Turkish,
  prices are in TRY, and the ToS is Turkish-law. Most likely exit location:
  Turkey. Treat as UNCONFIRMED — the exit IP/country must be measured
  after the first deploy.

## 9. Files in this package

| File | Purpose |
|---|---|
| `Dockerfile` | Alpine 3.21 + Xray-core v26.10.31 (pinned, verified tag 2026-11-22), runs as unprivileged user `xray` |
| `entrypoint.sh` | Generates the live config from env vars, starts Xray (+ front proxy) |
| `gen-config.py` | Renders `/tmp/xray-config.json` from `UUID` / `WS_PATH` / `PORT` / `FRONT_PROXY` / `LOGLEVEL` |
| `http-front.py` | Tiny proxy on `$PORT`: answers health checks with `200 ok`, forwards WS upgrades to Xray byte-for-byte |
| `config.example.json` | Rendered example of the config (reference only; live config is generated) |

Design notes:
- TLS terminates at DeployVera's edge, so Xray uses `security: none` and
  plain WS. The VLESS link therefore uses `security=tls` + `sni=<host>`
  (outer TLS) with `encryption=none`.
- Xray binds `127.0.0.1:10000` and the front proxy binds `0.0.0.0:$PORT`
  when `FRONT_PROXY=1` (default). This exists because PaaS health checks
  do a plain HTTP GET and expect 2xx, while Xray's WS inbound answers
  non-WS requests with 4xx — which can get the deploy rolled back as
  "unhealthy". Set `FRONT_PROXY=0` to run Xray directly on `$PORT` if the
  proxy ever causes trouble.
- Generated config goes to `/tmp` so nothing is written to the image at
  runtime. No capabilities, no privileged mode, no volumes needed.
- Private destinations are routed to `blackhole` (Xray `geoip:private`).

## 10. Deployment checklist

- [ ] 1. Generate a UUID: `uuidgen` (Linux/macOS) — keep it secret.
- [ ] 2. Create a GitHub/GitLab repo, commit this whole directory, push.
- [ ] 3. Sign up at https://deployvera.com/register?plan=container-free
         (name + email + password; verify the email).
- [ ] 4. Connect GitHub/GitLab in the panel (or use a public repo URL).
- [ ] 5. Create app → repo + branch → build method Dockerfile → port 8080.
- [ ] 6. Set env vars: `UUID=<your uuid>`, `WS_PATH=/vless`
         (leave `FRONT_PROXY=1`, `LOGLEVEL=warning` unless debugging).
- [ ] 7. Deploy; watch build logs. Build downloads Xray v26.10.31 from
         GitHub — if it 404s, bump `XRAY_VERSION` in the Dockerfile to the
         newest tag at https://github.com/XTLS/Xray-core/releases.
- [ ] 8. Note the live address, e.g. `https://<app>.deployvera.com`.
- [ ] 9. Health check: `curl -s https://<app>.deployvera.com/` must
         return `ok` (proves the front proxy + routing work).
- [ ] 10. WS check: `curl -s -i -H "Connection: Upgrade" -H "Upgrade:
         websocket" -H "Sec-WebSocket-Key: x" -H "Sec-WebSocket-Version: 13"
         https://<app>.deployvera.com/vless` — expect `101 Switching
         Protocols` (or at least a non-`426`/non-timeout response). If the
         upgrade is rejected or hangs, WebSocket does NOT pass through.
- [ ] 11. Build the Shadowrocket link (replace HOST, UUID, PATH):
         `vless://UUID@HOST:443?encryption=none&security=tls&sni=HOST&type=ws&host=HOST&path=%2Fvless#DeployVera`
- [ ] 12. Import into Shadowrocket, connect, check exit IP/country
         (e.g. visit https://ifconfig.me in the phone browser with the
         proxy on). Confirm the exit matches expectations.
- [ ] 13. If step 10 fails: try `FRONT_PROXY=0` + redeploy (rules out the
         front proxy), then try XHTTP transport instead of WS. If both
         fail, the platform proxy is the blocker — stop and report.

## 11. Blockers / unknowns (read before trying)

1. **WebSocket passthrough UNCONFIRMED** — no docs mention it. Live test
   (step 10) decides.
2. **Acceptable Use Policy text NOT retrieved** — the ToS has no proxy ban,
   but the AUP might. Read it in the browser first.
3. **Region UNCONFIRMED officially** — likely Turkey; exit location must be
   measured, not assumed.
4. **No transfer limit stated** — unknown whether the free plan caps
   bandwidth; watch usage after deploy.
5. **Captcha at signup unknown** — none visible in the fetched page text.
6. **Docker image NOT build-tested here** (no Docker in this VM). The
   Dockerfile is written from verified facts (Alpine 3.21 exists, Xray
   v26.10.31 tag + `Xray-linux-64.zip` asset naming confirmed via the
   release page), but the first platform build is the real test.
7. **Health-check behaviour unknown** — mitigated by the front proxy, but
   if DeployVera requires a specific path/status, adjust `http-front.py`.
8. `create_project` via MCP always needs browser approval; first deploy is
   easiest through the dashboard.
