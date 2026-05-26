---
title: "Browser User-Journey — 01 — The contract we build against"
version: v0.2.41
date: 2026-05-26
audience: Dev / Architect picking up the next slice
---

# 01 — The contract we build against

Everything here is **shipped and stable**. The user-journey platform treats this
document as the interface — additions need updates here; removals are breaking
changes. Two halves: the **execution substrate** (the stack on EC2) and the
**tool-API framework** (the operator/LLM experience).

> This consolidates the vault-app substrate contract
> (`v0.2.19__qa-vault-app/01`) with the TUI tool-API framework that the qa pack
> never touched. Both are dependencies of this platform.

---

## PART A — The execution substrate

### A1. The one-command deploy

```bash
sg vault-app create --with-playwright --wait
```

Produces a fresh EC2 host running, on the `vault-net` docker bridge:

| Service | Image | Port (host) | Port (bridge) | Role |
|---|---|---|---|---|
| sg-send-vault | sg-send-vault | `:443` HTTPS (real LE IP cert) | — | Vault: stores `journeys/` + `runs/`, sgit-versioned |
| sg-playwright | `diniscruz/sg-playwright` | `:80` HTTP | `:8000` | Browser-automation REST API |
| agent-mitmproxy | `agent_mitmproxy` | — | proxy `:8080`, mitmweb `:8081`, admin `:8000` | Transparent capturing proxy + control API |
| host-plane | `diniscruz/sg-host-control` | `:19009` (localhost on host) | `:8000` | Admin API: `/pods/*`, `/shell/*`, `/host/*`, Docker socket |

**Defaults:** TLS-on for the vault (Let's Encrypt IP cert). Playwright API on
**port 80** — chosen so sandboxes / egress-restricted environments reach it.
Each `/sequence/execute` call spawns and tears down **its own Chromium** (per-run
isolation), configured at launch with:

```yaml
SG_PLAYWRIGHT__DEFAULT_PROXY_URL:   http://agent-mitmproxy:8080
SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS: 'true'
```

→ **100% of browser traffic is captured** by mitmproxy with zero extra work.

### A2. Auth — one secret, two headers

A single per-stack access token, auto-generated at create, tagged on the EC2
instance as `AccessToken` (readable via `describe-instances`, no SSM).

| Header | Required by |
|---|---|
| `X-API-Key` | Every Playwright API call; every host-plane / mitmweb-admin / conductor call |
| `x-sgraph-access-token` | Every vault UI / Send API call |

### A3. The Playwright REST API (the engine the worker reuses)

| What | Value |
|---|---|
| Base (internal) | `http://sg-playwright:8000` |
| Auth | `X-API-Key` |
| The endpoint that matters | `POST /sequence/execute` — multi-step orchestration |
| Step vocabulary | `Enum__Step__Action` — 16 verbs (`navigate, click, fill, press, select, hover, scroll, wait_for, screenshot, video_start/stop, evaluate, dispatch_event, set_viewport, get_content, get_url`) |
| Boundary | `Step__Executor` is the **only** class that touches `page.*`. The platform never calls `page.*` directly — it composes sequences. |
| Agent guide | `library/guides/v0.2.6__playwright-api-for-agents.md` |

DOM-state assertions are done by appending **synthetic `wait_for` / `get_content`
steps** to the sequence, then reading their results back — so the boundary holds.

### A4. The mitmproxy capture surface — ✅ with one follow-up (we build it)

100% capture exists today; **per-run addressability does not**. This platform
**requires** it (you cannot aggregate flows across N workers without keying by
run). It is the qa-vault-app's "slice 4", now a prerequisite:

- Each worker injects `X-SG-Run-Id: <run_id>` into every browser request via the
  existing `Schema__Session__Credentials.extra_http_headers` channel — **no
  Playwright change**.
- `agent_mitmproxy` groups flows by that header in a ring buffer.
- New endpoint `GET /capture/network-log/{run_id}` returns that run's flows as
  NDJSON. (~80 lines: `Routes__Capture.py` + `Capture__Ring_Buffer.py` + intercept
  edits. Detail in `02` §3 and the qa pack `v0.2.19__qa-vault-app/02` §5.)
- Control API also exposes `/ca/cert`, `/ca/info`, `/config/interceptor`, `/metrics`.

Custom interceptors are loaded at create time via `--interceptor-script FILE`
(the vnc/firefox resolver pattern) → baked to `active.py`. "With and without
custom interceptors" = create with or without that flag.

### A5. Container fan-out primitives

| Primitive | Where | Capability | Limit |
|---|---|---|---|
| `POST /pods` | host-plane | start a container | `Schema__Pod__Start__Request` = `{name, image, ports, env, type_id}` — **no command/volume/limit override** |
| Docker socket | host-plane mounts `/var/run/docker.sock` (no `--privileged`) | full `docker run` (command, env, network, labels, `--cpus/--memory`) | root-equivalent host control (accepted pattern) |
| `Sidecar__Client` | `sg_compute/core/pod/Sidecar__Client.py` | typed client: `list_pods, get_pod, get_pod_logs, get_pod_stats, start_pod, stop_pod, remove_pod` | one pod at a time |

**Verdict:** because `/pods` cannot override the command, the **conductor fans
workers out via the Docker socket** (the same access host-plane already has).
Arbitrary images are allowed; the platform's new images publish to **Docker Hub**
(public, under the `diniscruz/` namespace like `diniscruz/sg-playwright` /
`diniscruz/sg-host-control`), so **no registry auth is needed at pull time** —
not ECR.

### A6. Stack lifecycle CLI (reused verbatim)

`sg vault-app {create,list,info,wait,health,diag,logs,exec,connect,open,cert,extend,recreate,delete,ami}` — every verb auto-resolves the stack name when only one exists. `info` and EC2 tags carry the URL set + `AccessToken`.

---

## PART B — The tool-API framework (the operator + LLM experience)

This is the half the qa pack never used. It is **backend-neutral** and
**audit-safe**, and it is exactly the seam for "TUI API workflows + chat talk-to-
the-tools".

### B1. The agentic chat loop — backend-neutral

`sgraph_ai_service_playwright__cli/tui/chat/service/Chat__Engine.py`

- `send_turn(...)` — streaming, no tools.
- `send_turn_agentic(session, text, center, tools, name_map, grants, max_steps=6)`
  — the tool loop: calls `backend.converse(...)`; on a `tool_use` block, looks up
  `(slug, action)` via `name_map` and dispatches through
  `center.execute(slug, action, input, grants)`; feeds the result back (honest on
  `error` / `dry_run` / `preview`). **100% backend-neutral** — backends only adapt
  wire format.

Backends (`tui/chat/backend/Chat__Backend.py`, abstract): `bedrock`, `ollama`,
`openrouter`, `in-memory`. Each implements `models / capabilities / cost /
stream_turn / converse`. Selected by injection.

### B2. Tools — pure data, sanitized names

- `Schema__Chat__Tool` = `{name, description, input_schema: dict}` (JSON Schema).
- `Chat__Tool__Builder.build(granted_actions)` → `(tools, name_map)`, where
  `name_map: sanitised_name → (slug, action)`.

### B3. The execution center — the safety gate (`tui/tool_api/service/Tui_Api__Execution_Center.py`)

`execute(slug, action, params, grants)` runs, in order:

1. **Registry lookup** of the provider.
2. **Precondition / sequencing** check (`provider.state()`).
3. **Param validation** against the action's JSON Schema.
4. **Grants** check (SG/Role capability tokens cover the action).
5. **IAM privilege pre-flight** (backing AWS permissions present).
6. **Dry-run preview** (if `supports_dry_run`).
7. **Mutation gate** — mutating actions need an env-var allow **or** a confirm
   callback; otherwise returns a dry-run result with the preview.
8. **Dispatch** `provider.dispatch(action, params)`.
9. **Audit log**.

This is why cost-bearing operations (scaling workers!) are safe by construction.

### B4. Providers + workflows

- `Tui_Api__Provider` (subclass): `manifest()` → `Schema__Tui_Api__Manifest`
  of `Schema__Tui_Api__Action`s (`name, description, input_schema, scope,
  preconditions, privileges, supports_dry_run`); `dispatch(action, params)`.
- `Tui_Api__Registry.register(provider)`; `Tui_Api__Loadout__Assembler.from_tools("ns.x:read")`.
- **`Schema__Tui_Api__Workflow`** = `{name, description, grants}` — a curated
  capability bundle. **The model never picks tools; a workflow curates grants.**

### B5. The chat TUI (the screen to clone)

`aws/bedrock/tui/screens/Bedrock__Chat__Screen.py` — a thin Textual `App`. Widgets:
transcript (`Chat__Bubble`), `Chat__Composer`, `Chat__Inspector` (f2),
`Chat__Cost__Meter`, `Chat__Vfs__Browser` (f3), `Chat__Doc__Chips`, and
`Chat__Tool_Calls` (a collapsed/expandable tool-call card). Streaming uses
`@work(exclusive=True, group='llm')` + `call_from_thread()`; the agentic path is
non-streaming (tools block). **A new cockpit clones this layout, injects the same
engine, and registers its own provider.**

---

## C. Test status (substrate, as of `dev`)

- `sg_compute_specs/vault_app/tests/`: **63 passing**.
- `sg_compute__tests/platforms/tls/`, `…/fast_api/`: passing on py3.12.
- TUI/chat: import-guarded Textual tests; in-memory chat backend exercises the
  agentic loop with scripted tool-use (no mocks).

---

*Next: `02__platform-design.md` — the conductor, the worker, the suites, the schemas, and the slice plan.*
