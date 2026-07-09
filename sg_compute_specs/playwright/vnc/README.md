---
title:  sg-playwright-vnc — build / run / verify
status: P1 of team/comms/plans/v0.2.67__sg-playwright-vnc__interactive-browser-image.md
---

# sg-playwright-vnc

The sg-playwright service image plus a visible desktop: Xvfb (`:99`) + openbox +
x11vnc (container-internal `:5900`) + noVNC/websockify (`:6080`), supervised by
supervisord alongside the unchanged FastAPI service (`:8000`). Headed browser
launches render on `:99` and are watchable/drivable at `:6080` — the same
browser is reachable through the API and the human viewer.

## Build (from repo root)

```bash
docker build -f sg_compute_specs/playwright/vnc/Dockerfile \
             -t diniscruz/sg-playwright-vnc:local .

# CI pins the base to the run's own by-digest image:
docker build --build-arg BASE_IMAGE=diniscruz/sg-playwright@sha256:<digest> \
             -f sg_compute_specs/playwright/vnc/Dockerfile \
             -t diniscruz/sg-playwright-vnc:<version> .
```

## Run + verify (the P1 exit criteria)

```bash
docker run -d --name pw-vnc -p 8000:8000 -p 6080:6080 \
  -e FAST_API__AUTH__API_KEY__VALUE=local-key \
  diniscruz/sg-playwright-vnc:local

# 1. the API tier is unaffected by the desktop layer
curl -sf -H 'X-API-Key: local-key' http://localhost:8000/health/status

# 2. noVNC serves
curl -sf -o /dev/null -w '%{http_code}\n' http://localhost:6080/vnc.html   # → 200

# 3. all supervised programs run
docker exec pw-vnc supervisorctl status         # xvfb/openbox/x11vnc/novnc/fastapi RUNNING

# 4. a headed browser is visible: open http://localhost:6080/vnc.html → Connect,
#    then launch one on the display (P2 adds POST /desktop/browser; until then):
docker exec -e DISPLAY=:99 pw-vnc python3 -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=False, args=['--no-sandbox'])
pg = b.new_page(); pg.goto('https://example.com'); pg.wait_for_timeout(60000)"
#    → the browser window appears in the noVNC tab
```

## The sub-path proof (the jlesage killer, settled here)

```bash
docker compose -f sg_compute_specs/playwright/vnc/spike/docker-compose.yml up -d
# open https://localhost/browser/1/  (accept the internal-CA warning)
# PASS = the noVNC desktop connects: assets load AND the websocket survives the
#        path-stripping reverse proxy. This is the exact edge shape content_proxy
#        P3 ships (/browser/{i} → :6080).
```

## Env flags

| Var | Effect |
|---|---|
| `SG_PLAYWRIGHT__DISPLAY_MODE` | `vnc` (baked into this image) → service defaults headed launches onto `:99`; `headless` → base-image behaviour |
| `SG_PLAYWRIGHT__AUTOSTART_BROWSER` | `chromium` / `firefox` → oneshot opens a headed browser via `POST /desktop/browser` once the API is up |
| `SG_PLAYWRIGHT__AUTOSTART_START_URL` | start page for the autostarted browser (default `about:blank`) |
| `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` | (existing) every launch goes through this proxy — content_proxy points it at `mitmproxy-int:8080` |
| `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` | (existing) accept the mitmproxy CA without any profile/certutil work |

## Security

- `:5900` (raw VNC) is `-localhost` — unreachable from outside the container.
- `:6080` (noVNC) has no auth of its own; the content_proxy edge gate
  (`--edge-auth`) is the auth story, same as `/pw`.
