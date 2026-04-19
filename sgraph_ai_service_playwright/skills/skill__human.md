# SKILL — sg-playwright (human operator)

_Status: FIRST-PASS PLACEHOLDER (v0.1.29). TODO — expand before v0.2._

## What this service does

`sg-playwright` is a browser-automation API for the SG/Send ecosystem. It runs
identically on a laptop, in CI, on Claude Web, on Fargate, and on Lambda — one
Docker image, five deployment targets. The declarative step language lets you
script a browser session without writing Playwright code directly.

## Quick orientation

- **Health**: `GET /health/info` — service version, Chromium version, code source.
- **Admin**: `GET /admin/manifest` — points at OpenAPI + SKILLs + capabilities.
- **OpenAPI**: `GET /openapi.json` — full machine-readable route catalogue.
- **Capabilities**: `GET /admin/capabilities` — declared axioms, future lockdown layers.

## Common flows

- **One-shot browser action** — POST `/browser/navigate`, `/browser/click`,
  `/browser/screenshot` etc. Each request spins up fresh Chromium, runs the
  action, tears down. Stateless between calls.
- **Multi-step sequence** — POST `/sequence/execute` with a Type_Safe
  `Schema__Sequence` body. Steps run in order; artefacts collected per step.
- **Auth cookies** — `GET /auth/set-cookie-form` (HTML), `POST /auth/set-auth-cookie`
  for wiring SG_SEND vault-backed sessions.

## Deploying (v0.1.29)

```bash
python scripts/deploy_code.py --stage dev       # ~30s cloud round-trip
```

Rollback = flip `AGENTIC_APP_VERSION` back to an older pinned version. The S3
bucket is append-only; every version you ever shipped is still there.

## Debugging

- `/admin/health` — `loaded` vs `degraded`. `degraded` means the boot shim
  caught an import error.
- `/admin/error` — last failed-load error string.
- `/admin/boot-log` — last N boot-shim log lines.
- `/admin/env` — current `AGENTIC_*` env vars (redacted — no secrets leak).

## TODO before v0.2

- Expand failure-mode triage tree.
- Document the common `Schema__Sequence` patterns with examples.
- Add a "first session checklist" for a brand-new operator.
