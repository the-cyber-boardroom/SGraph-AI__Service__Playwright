# SKILL — sg-playwright (LLM agent)

_Status: FIRST-PASS PLACEHOLDER (v0.1.29). TODO — expand before v0.2._

## What you are talking to

`sg-playwright` is a self-describing HTTP surface for browser automation.
Every endpoint is typed; every response is a `Schema__*` wire contract. You
do not need to guess shapes — read the manifest and the OpenAPI doc.

## Discovery

1. Fetch `GET /admin/manifest`. It points at:
   - `openapi_path`      — full route catalogue.
   - `capabilities_path` — axioms + declared narrowing.
   - `skills`            — `{ human, browser, agent }` — this file is `agent`.
2. Fetch `GET /admin/info` for app name / stage / version / code source.
3. Fetch `GET /admin/capabilities` for declared axioms. In v0.1.29 the axiom
   list is `["statelessness", "least-privilege-by-declaration", "self-description"]`
   and `declared_narrowing` is empty (lockdown layers are deferred).

## Decision recipes

### "Is this API alive and on the version I expect?"
- `GET /admin/health` → `{status: "loaded"|"degraded", code_source: "..."}`.
- `GET /admin/info`   → confirms `app_version` matches what you pinned.

### "I need to automate a browser task."
- One-shot action: POST to the relevant `/browser/*` endpoint.
- Multi-step flow: POST to `/sequence/execute` with a `Schema__Sequence`.
- Always set `headless: true` unless you are in an interactive debugging session.

### "Something broke."
- `GET /admin/error` — the last boot-time error.
- `GET /admin/boot-log` — recent boot trail.
- `GET /admin/env` — AGENTIC_* env vars (redacted view; never leaks secrets).

## Axioms you can rely on

- **Statelessness.** No wire-visible sessions.
- **Least-privilege-by-declaration.** `evaluate` is allow-list gated; no ad-hoc JS.
- **Self-description.** The manifest + OpenAPI + this SKILL are enough to onboard.

## TODO before v0.2

- Prompt templates for common agent tasks (screenshot → vision model → next action).
- Failure taxonomy: when to retry, when to escalate, when to abort.
- Worked examples with inline JSON bodies.
