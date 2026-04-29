# 01 — Architecture sketch (Option 1, FastAPI auth sidecar)

## Container layout

```
┌─────────────────────────────────────────────────────────┐
│ EC2 host (al2023)                                       │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   sg-nginx   │───▶│  sg-chromium │    │  sg-mitm   │ │
│  │  TLS, 443    │ ╲  │  noVNC :3000 │    │  :8080/8081│ │
│  └──────┬───────┘  ╲ └──────────────┘    └────────────┘ │
│         │           ╲                                   │
│         │ auth_request                                  │
│         ▼            ╲                                  │
│  ┌──────────────┐                                       │
│  │   sg-auth    │  ← NEW — branded login page +         │
│  │  FastAPI :8K │    cookie verifier                    │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

All four containers on the same `sg-net` bridge. Only `sg-nginx` exposes
443. `sg-auth` is loopback-on-bridge only.

## Request flow

```
operator                                                                 sg-nginx        sg-auth         sg-chromium
   │  GET / (no cookie)                                                    │
   ├─────────────────────────────────────────────────────────────────────▶ │
   │                                  auth_request /auth                   │ ─────────▶  │ 401 (no cookie)
   │  302 → /login?next=/                                                  │ ◀─────────  │
   │ ◀────────────────────────────────────────────────────────────────────│
   │  GET /login                                                           │
   ├─────────────────────────────────────────────────────────────────────▶ │ ─────────▶  │ 200 HTML form
   │                                                                       │
   │  POST /login (password=…)                                             │
   ├─────────────────────────────────────────────────────────────────────▶ │ ─────────▶  │ verify bcrypt; Set-Cookie sg-vnc-session=<HMAC>; 302 /
   │                                                                       │
   │  GET / (with cookie)                                                  │
   ├─────────────────────────────────────────────────────────────────────▶ │
   │                                   auth_request /auth                  │ ─────────▶  │ 200 (HMAC ok)
   │                                   X-Forwarded-User: operator          │ ◀─────────  │
   │                                   ──────────────── proxy_pass         │ ──────────────────────▶ │ noVNC stream
   │ ◀────────────────────────────────────────────────────────────────────│ ◀────────────────────── │
```

## sg-auth service shape

Following `team/roles/architect/ROLE.md` patterns:

```
sgraph_ai_service_playwright__cli/vnc/auth_sidecar/
├── service/
│   ├── Vnc__Auth__Sidecar.py        (Tier-1: FastAPI app factory)
│   ├── Cookie__Token__Codec.py      (HMAC-sign / verify session token)
│   └── Password__Verifier.py        (bcrypt verify against the htpasswd file)
├── schemas/
│   ├── Schema__Login__Request.py
│   └── Schema__Login__Response.py
├── fast_api/routes/
│   ├── Routes__Login.py             (GET /login form, POST /login, POST /logout)
│   └── Routes__Auth.py              (GET /auth — nginx auth_request endpoint)
└── docker/
    └── Dockerfile                   (python:3.12-slim + uvicorn)
```

The Docker image bakes only the `vnc/auth_sidecar/` package — small (~80MB).
Built once, pinned in `Vnc__Compose__Template.AUTH_SIDECAR_IMAGE`.

Reuses **the same htpasswd file** that nginx already mounts — no duplicate
state. The verifier reads `/etc/sg-vnc/htpasswd:ro` and runs `bcrypt.verify`.

## What changes in this repo

| Where | Change |
|---|---|
| `Vnc__Compose__Template.py` | Add `sg-auth` service, swap `auth_basic` for `auth_request` block |
| `Vnc__User_Data__Builder.py` | Mount `/opt/sg-vnc/auth/secret` (HMAC key — generated at boot) into sg-auth |
| `Vnc__HTTP__Probe.py` | Probe `/login` (200) instead of needing Basic-auth creds |
| `scripts/vnc.py` | `--password` flag stays the same; `username` constant stays `operator` |
| New | `vnc/auth_sidecar/` package per layout above |
| New | `sgraph_ai_service_playwright__cli/vnc/docker/images/auth_sidecar/` Dockerfile + image build |

## What stays the same

- The bcrypt hash is still in `/opt/sg-vnc/nginx/htpasswd` (now also read by
  `sg-auth`).
- mitmweb auth keeps its existing `--proxyauth` file (unchanged).
- The `--password` and `--open` CLI flags are unchanged.
- The `Vnc__Service.create_stack` API is unchanged.

## What this unlocks

- The Admin UI iframe pane (`v0.1.118__admin-ui-vnc-iframe-pane/`) becomes
  trivial — no more "pre-warm fetch" hack. The cookie set by `/login` is
  inherited by the iframe automatically.
- A logout button in the admin UI just calls `POST /logout`.
- Future: per-stack OAuth ("login with GitHub" → must be a member of
  `the-cyber-boardroom`) drops in as a new route on the same sidecar.
