# playwright-service — Proposed

PROPOSED — does not exist yet. Items below extend the Playwright service surface but are not in code today.

Last updated: 2026-05-17 | Domain: `playwright-service/`
Source: distributed from `_archive/v0.1.31/05__proposed.md` ("Playwright (carried forward)" section) plus the v0.1.24 deferred items still open.

---

## P-1 · `AGENTIC_ADMIN_MODE=full` with `POST /admin/reload`

**What:** Today the admin surface is read-only. The full mode would expose a `POST /admin/reload` to refresh code / capabilities without a Lambda redeploy.

**Required:** an auth model (the read-only admin endpoints intentionally bypass the API-key middleware; a mutation endpoint cannot). Currently deferred until that auth model exists.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-2 · Per-layer SKILL files for `agentic_fastapi` and `agentic_fastapi_aws`

**What:** Each L1/L2 layer would ship its own markdown SKILL file at `/admin/skills/{layer}` so agents can introspect per-layer guidance.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-3 · Lockdown layers / declared narrowing

**What:** `declared_narrowing` ships as `[]` today. Populate it with the actual narrowing claims (e.g. "this Lambda cannot reach the internet without proxy", "no eval"). Cross-references the security domain.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-4 · Repo split into `api/` + `container/` packages

**What:** Separate the pure-FastAPI surface from the Lambda-Web-Adapter / container concerns.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-5 · PyPI publishing of `agentic_fastapi` / `agentic_fastapi_aws`

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-6 · Sidecar enforcement layer

**What:** Mechanism to guarantee `agent_mitmproxy` is up before the Playwright service accepts requests; today the sidecar comes up alongside via `docker compose` but there is no health-gate.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-7 · Two-track CI pipeline split

**What:** Separate fast unit-test workflow from the full-build pipeline.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-8 · 10 deferred `Step__Executor` action handlers (v0.1.24 carryover)

**What:** The brief lists 10 action verbs (e.g. wait, hover, double-click, drag, select-option, upload-file, …) not yet implemented in `Step__Executor`.

**Source:** v0.1.24 deferred list (carried forward via `_archive/v0.1.31/05__proposed.md`).

## P-9 · Warm-browser pool

**What:** Keep N browser contexts warm in-process to avoid the cold-start launch cost per request.

**Source:** v0.1.24 deferred list.

## P-10 · `POST /browser/batch`

**What:** Multi-step batch endpoint distinct from `/sequence/execute` — fire-and-forget batch with bulk semantics.

**Source:** v0.1.24 deferred list.

## P-11 · Per-route API-key scoping

**What:** Today a single `FAST_API__AUTH__API_KEY__VALUE` gates everything. A capability-style token would let one key be screenshot-only, another sequence-only, etc. Cross-references host-control P-2 (RBAC for host endpoints).

**Source:** v0.1.24 deferred list.

## P-12 · Client registration helpers

**What:** First-class registration helpers around `register_playwright_service__in_memory()` for downstream callers (osbot ecosystem etc.).

**Source:** v0.1.24 deferred list.
