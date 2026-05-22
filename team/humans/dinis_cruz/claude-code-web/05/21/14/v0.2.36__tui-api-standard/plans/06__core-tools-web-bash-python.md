---
title: "Core tools — Web Access, Bash, Python (plan)"
file: 06__core-tools-web-bash-python.md
author: Architect (Claude)
date: 2026-05-22 (UTC hour 09)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — for ratification. Extends the built core-tool pattern (VFS) with three more.
parent: 00__plans-index.md
grounds_on:
  - 01__tui-api-contract-and-conventions.md   # the standard these tools obey
  - "the built VFS core tool (cli/tui/tool_api/core/vfs/) — the template for a core tool"
  - "sg_compute_specs/playwright — the Playwright step/sequence primitives (reused for web.render)"
  - "cli/docker + cli/podman — EC2 Docker-stack tooling (context, NOT a command-exec primitive)"
---

# Core tools: Web Access · Bash · Python

> The standard already named these as the next core tools (§9 "the pattern generalises:
> web fetch / search (READ_ONLY, NETWORK privilege) and code execution (DESTRUCTIVE,
> sandbox privilege)"). This plan designs all three as **`Tui_Api__Provider`s** — same
> contract, same execution center, same loadout, same inspector/tool-cards, same VFS — so
> they inherit gating, sequencing, audit, and cost for free. **Disabled by default**, granted
> per loadout; bash/python are DESTRUCTIVE and always gated.

---

## 1. Reused vs. new (honest)

| Reused (already built / exists) | New (this plan builds) |
|---|---|
| The TUI API contract, SG/Role scopes, **execution center** (confirm/dry-run/`ALLOW_MUTATIONS`/audit), loadout, the chat's collapsed **tool-call cards** + **F2 inspector**, the **VFS** core tool | A **`Container__Exec`** substrate (run a command in an ephemeral container) — the repo has **no** command-exec primitive today |
| The **Playwright** browser core (`sg_compute_specs/playwright` step/sequence primitives) — reused for `web.render` of JS pages (on-brand: this IS a browser-automation service) | An **HTTP fetch + SSRF/allowlist** guard (no general web-egress guard exists; closest is the evaluate-action `JS__Expression__Allowlist` deny-by-default philosophy) |
| `cli/docker` + `cli/podman` (Docker **stack on EC2** tooling) — *context only*; it deploys the service image, it does not exec commands | A **local-disk (temp-folder) VFS backend** (`memory_fs`'s `Storage_FS__Local_Disk`, plus a `vfs_root_path()`) so the container can **bind-mount the VFS dir** as `/work` |

**Deployment constraint (must flag):** spawning containers needs a **container runtime on the
host** (laptop / EC2 / a container-capable Fargate task). It does **not** work inside Lambda.
So bash/python register only where a runtime is reachable — exactly like the VFS tool registers
only where `memory_fs` is importable. Web access has no such constraint (just outbound network).

---

## 2. Tool 1 — Web Access  (`core.web`, READ_ONLY)

Lets the agent read the web on demand. Tier **READ_ONLY**; privilege **NETWORK** + a domain
**allowlist** (deny-by-default).

| action | params | does |
|---|---|---|
| `web.fetch` | `url`, `max_bytes?` | HTTP GET via httpx → returns **text** (HTML stripped to readable text/markdown), status, final URL |
| `web.render` | `url`, `wait_for?` | drives the **Playwright** primitives (goto + extract rendered text) for JS-heavy pages |
| `web.search` | `query`, `count?` | search results — **deferred** (needs a search backend + key; a later, separately-privileged action) |

**Security (the heart of a web tool):**
- **SSRF guard** — resolve the host and **refuse private / loopback / link-local / cloud-metadata**
  targets (`127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254.169.254`, `::1`, …).
- **Domain allowlist** — deny-by-default `Schema__Web__Allowlist` (mirror `JS__Expression__Allowlist`);
  a `web:network` grant may scope to specific domains (the SG/Role `resource` field: `core.web:read:github.com`).
- **Caps** — max bytes, timeout, max redirects, content-type allowlist (text/html/json/markdown).
- READ_ONLY → runs in AUTO, but the **NETWORK privilege** must be present (the resolver checks it).

**Synergy with the VFS:** the agent can `web.fetch` a page and `vfs.write` it — caching reference
material in the session VFS, then reading it later for ~zero token cost (the files-as-tool pattern).

---

## 3. Tools 2 + 3 — Bash + Python  (`core.bash`, `core.python`, DESTRUCTIVE)

Arbitrary command/code execution in an **ephemeral container**. Tier **DESTRUCTIVE**; privilege
**SANDBOX** (a container runtime). **Always gated** — the execution center requires confirm +
`..._ALLOW_MUTATIONS`, exactly as it does for `vfs.delete` today.

| action | params | does |
|---|---|---|
| `bash.run` | `command`, `timeout?` | run in a tiny Linux container (busybox/alpine/debian-slim) → `{stdout, stderr, exit_code, duration}` |
| `python.run` | `code`, `timeout?` | run in a python container (`python:3.12-slim` / `python:alpine`) → same shape |

Both sit on the shared **`Container__Exec`** substrate (§4). The model's call → the execution
center (gated/audited) → `Container__Exec.run(...)` → the result is fed back **truthfully** (the
same honest-tool-result path just added), and shown in the collapsed tool-call card + inspector.

**VFS as the working directory (the powerful bit) — via a temp-folder VFS backend.**
Prerequisite: extend the built VFS core tool to optionally back its storage with a **local
temp folder** (`memory_fs` already ships `Storage_FS__Local_Disk`) instead of in-memory.
When bash/python are enabled, the session VFS uses a per-session **temp dir**, and the
container **mounts that exact dir** as `/work` (read-write). No materialise/sync round-trip —
**the folder *is* the shared state**: `vfs.write` (tool), the container's file I/O, and the
**F3** browser all read/write the same directory. So `web.fetch → vfs.write → python.run
(reads/writes /work) → vfs.read` is one coherent workflow with a single source of truth.

> The VFS provider gains a `vfs_root_path()` (the host dir, when the backend is local-disk)
> so the exec substrate knows what to mount. Default stays in-memory + ephemeral (decision
> §8 #8); the local-disk backend is auto-selected when a container tool is in the loadout.

---

## 4. The `Container__Exec` substrate (new infra)

```python
class Container__Exec(Type_Safe):                          # interface
    def run(self, image: str, argv: list, *, stdin: str = '', workdir_path: str = None,
            timeout_s: int = 30, network: bool = False) -> Schema__Exec__Result: ...
# workdir_path = the VFS temp dir to bind-mount as /work (RW); Schema__Exec__Result: stdout · stderr · exit_code · duration_ms · timed_out
```

- **Real runner** (`Container__Exec__Docker` / `__Podman`): `docker run --rm` with hardening —
  `--network none` (default), non-root user, `--read-only` rootfs + the VFS temp dir
  **bind-mounted** at `/work` (`-v {workdir_path}:/work`), `--memory`/`--cpus` caps,
  `--pids-limit`, drop capabilities, and a hard **timeout kill**. The mount means changes are
  live in the VFS the instant the container writes them. Uses the docker/podman CLI on a
  container-capable host. (osbot-aws is for AWS, not local docker — this is local subprocess/SDK.)
- **In-memory fake** (`Container__Exec__In_Memory`): scripted `{argv → result}` for **no-mock tests**
  of bash/python providers + the gating, with **no Docker** — so the provider/loadout/engine tests
  run anywhere (the real runner is gated, like the Textual/memory_fs suites).
- **Isolation defaults:** network **off**, non-root, read-only rootfs, resource caps, ephemeral
  (`--rm`), no host mounts except `/work` (the VFS). A higher-privilege "network-on" tier is a later
  add (for `pip install` etc.) — v1 assumes pre-baked images + stdlib.

---

## 5. Security model (summary)

| tool | tier | privilege | gate | isolation |
|---|---|---|---|---|
| `core.web` | READ_ONLY | NETWORK (+ domain allowlist) | AUTO, but NETWORK priv enforced; SSRF + allowlist + caps | egress-only, no exec |
| `core.bash` | DESTRUCTIVE | SANDBOX (container runtime) | confirm + `SG_TUI_API__ALLOW_MUTATIONS` | ephemeral container, network-off, non-root, ro-rootfs, capped, timeout |
| `core.python` | DESTRUCTIVE | SANDBOX | same | same |

All three: discoverable via `sg <area> tui api`, scoped by **SG/Role** (`core.web:read`,
`core.bash:run`, `core.python:run`), every call **audited** in the ring buffer, surfaced in the
**tool-call cards** + **F2 inspector**, and **off until granted** in the loadout. "Damage limitation
by not giving privileges" (brief 2) is the default: a bare chat has none of these.

---

## 6. How it shows up in the chat (no new UI)

Everything reuses what's built:
- `sg aws bedrock chat tui --tools 'core.web:read,core.python:run'` (or `ctrl+g`) grants them.
- The agentic loop calls them; the **collapsed tool-call card** shows `🔧 web.fetch, python.run`;
  expand for request/response; **F2** shows the exact Converse `toolConfig`; **F3** shows files the
  tools wrote to the VFS; per-turn cost sums model + tool round-trips (exec adds latency/§cost).
- A gated `bash.run` without `ALLOW_MUTATIONS` is **visibly refused** (the honest-result path) — the
  model can't pretend it ran.

---

## 7. Slice plan (pure-first; real runtimes gated)

| Slice | Scope | Tests |
|---|---|---|
| **W1 — web.fetch** | httpx GET + HTML→text + SSRF guard + domain allowlist + caps; READ_ONLY provider | in-memory fake HTTP (no network) |
| **W2 — web.render** | drive the Playwright step/sequence primitives for JS pages | gated (needs chromium) |
| **W3 — web.search** | a search backend behind a key/privilege | deferred |
| **V-local — VFS temp-folder backend** *(prerequisite for X1/X2)* | extend the built VFS tool: a `Storage_FS__Local_Disk` (per-session temp dir) backend + `vfs_root_path()`; default stays in-memory, auto-switch to local when a container tool is loaded | 3.12-gated (CRUD over a temp dir; path exposed) |
| **X0 — Container__Exec** | the substrate: interface + `__In_Memory` fake + a real docker/podman runner with the hardening flags; bind-mounts `workdir_path` as `/work` | fake (anywhere) + real (gated on a runtime) |
| **X1 — bash.run** | provider over the substrate; DESTRUCTIVE, gated; truthful result; `/work` = the VFS temp dir | in-memory exec |
| **X2 — python.run** | provider over the substrate; DESTRUCTIVE, gated; `/work` = the VFS temp dir | in-memory exec |
| **X3 — VFS↔container coherence** | wire the VFS temp dir as the bind-mounted `/work` (no copy); F3 + tools + container share it | in-memory exec + local-disk VFS |

Build order: **W1** (safe, high-value, pure-ish) → **V-local** (the temp-folder VFS backend —
the share mechanism) → **X0** (the substrate) → **X1/X2** (bash/python, gated for real) →
**X3** (wire the temp dir as `/work`) → **W2** (Playwright render) → W3 later.
Each is a core tool under `cli/tui/tool_api/core/{web,bash,python}/`, disabled by default.

---

## 8. Decisions to ratify

| # | Question | Recommendation |
|---|---|---|
| 1 | Per-call vs per-session container | **Per-session** container reused across calls (faster, and `/work` persists between bash/python calls); torn down on session close. Per-call is the stricter-isolation fallback. |
| 1b | VFS backend when containers are used | **Auto-switch to `Storage_FS__Local_Disk`** (a per-session temp dir) so it can be bind-mounted; default stays in-memory when no container tool is loaded. Temp dir lifecycle = session (created on enable, removed on close — ephemeral on disk). Bind RW. |
| 2 | Network in exec containers | **Off by default.** No `pip install`/`apt` at run time → use pre-baked images + stdlib. A separate higher-privilege "network-on" tier later. |
| 3 | Base images | `busybox`/`alpine` (bash), `python:3.12-slim` (python) — pin digests; keep small. |
| 4 | Where exec runs | v1: **local/host Docker** (the operator's machine or the EC2 the TUI runs on). A remote exec service (SSM/Fargate task) is a later option. **Never Lambda.** |
| 5 | web.search backend | Deferred; when added, behind its own key + NETWORK privilege. |
| 6 | Exec cost model | Track **duration** (and a notional $/sec) on the audit Call; tokens are the LLM's, exec is wall-clock. |
| 7 | Default loadout | None of these on by default. Web read is the safest to grant; bash/python require explicit grant + confirm + `ALLOW_MUTATIONS`. |

---

## 9. Real vs PROPOSED

| Thing | Status |
|---|---|
| The core-tool pattern + the VFS as its template | **EXISTS** (built) |
| The execution center gating/audit, loadout, tool-cards, inspector, VFS browser | **EXISTS** |
| Playwright step/sequence primitives (for web.render) | **EXISTS** (`sg_compute_specs/playwright`) |
| `memory_fs` local-disk backend (`Storage_FS__Local_Disk`) — the temp-folder substrate | **EXISTS** (PyPI) — just needs wiring into the VFS provider + a `vfs_root_path()` |
| `Container__Exec` substrate, web/bash/python providers, SSRF/allowlist guard, the temp-folder VFS backend + bind-mount | **PROPOSED — does not exist yet** |
| A container-exec primitive in `cli/docker` | **does not exist** — that tooling deploys the service to EC2, it does not exec commands |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
