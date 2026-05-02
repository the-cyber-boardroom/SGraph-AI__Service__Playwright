# host-control — Proposed

PROPOSED — does not exist yet. Items below extend the host-control plane but are not in code today.

Last updated: 2026-05-02 | Domain: `host-control/`

---

## P-1 · WebSocket shell hardening

**What:** The current `WS /shell/stream` spawns `/bin/rbash` with no per-message ratelimiting, no idle-timeout, no audit logging, and no resource cap. A hostile client could spawn long-running processes inside `rbash` that survive the WebSocket close.

**Required:**

- Idle timeout (default: 300 s) closing the WS and SIGKILLing the process tree.
- Per-message rate limit on `receive_bytes` to bound write throughput.
- Audit log entry per command line (delimited by newline). Format TBD; aligns with the JS-allowlist audit pattern for `Step__Executor`.
- Process-tree kill on close, not just `proc.kill()` (which leaves children if `rbash` forked).

**Source:** Boundary risk noted by the UI Architect post-fractal-UI brief (`team/comms/briefs/v0.1.140__post-fractal-ui__backend/`) — "shell endpoints exist but the security envelope is thin."

## P-2 · RBAC for host endpoints

**What:** Today the entire host-control surface sits behind a single `FAST_API__AUTH__API_KEY__VALUE`. There is no per-action authorisation: the same key that reads `/host/status` can also issue `DELETE /containers/{name}` and connect to `WS /shell/stream`.

**Required:**

- A capability vocabulary on the host token: `host.read`, `host.containers.write`, `host.shell.execute`, `host.shell.stream`.
- Token issuance (likely from the SP CLI control plane) carries the capability set.
- Per-route capability check.

**Source:** Same brief as P-1.

## P-3 · Runtime auto-detection feedback in UI

**What:** `GET /host/runtime` returns docker / podman / none. The dashboard does not yet surface this on the per-stack detail page; users cannot tell which runtime is running on a given host without curl-ing.

**Required:**

- Dashboard reads `host_api_url` from the EC2 instance info, calls `/host/runtime`, displays the result on the per-stack detail and on the right-info-column status panel.
- Visual treatment when `runtime: 'none'` (host-control image missing) — prominent error state.

**Source:** UI implication of the container-runtime-abstraction brief (`team/comms/briefs/v0.1.140__post-fractal-ui__frontend/04__cleanup-pass.md` open question 1, plus the briefs/05/01 brief).

## P-4 · Sidecar attachment

**What:** The container-runtime brief gestures at attaching sidecars (MITM proxy, Neko, desktop streaming) to a running primary container. The host plane does not yet support this — `POST /containers` starts a single container.

**Required:**

- A new endpoint family for sidecar lifecycle: attach (`POST /containers/{name}/sidecars`), list (`GET .../sidecars`), detach (`DELETE .../sidecars/{sidecar_id}`).
- Sidecar manifest format: container image, network mode (`shared`, `bridge`), env, volumes.
- Privileged-container indicator in `Schema__Container__Info`.

**Source:** `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__container-runtime-abstraction.md` (sections on sidecar attachment).

## P-5 · Long-running vs ephemeral container modes

**What:** The container-runtime brief calls for a "container mode" selector at start time (long-running with restart policy, ephemeral with auto-cleanup). Today `Schema__Container__Start__Request` has no such field.

**Required:**

- Field `mode: Enum__Container__Mode` (`LONG_RUNNING` / `EPHEMERAL`) on the start request.
- `Container__Runtime` adapters honour the mode (set restart policy, set auto-remove flag).
- Reflected in `Schema__Container__Info`.

**Source:** Same brief.

## P-6 · Larger allowlist for `/shell/execute`

**What:** The current 15-entry allowlist (docker / podman read-only commands + a handful of OS metrics) is sufficient for diagnostics but cannot cover legitimate ops needs (e.g. `journalctl -u <service>`, `top -bn1`, `vmstat`).

**Required:**

- A justified expansion of `SHELL_COMMAND_ALLOWLIST` driven by real ops use-cases.
- AppSec sign-off on every addition.
- The `/shell/stream` (rbash) path remains the escape hatch for anything not in the allowlist.

**Source:** Operational pragmatism — not yet a written brief.

## P-7 · Streaming logs

**What:** `GET /containers/{name}/logs` returns a `tail`-bounded snapshot. There is no streaming-logs endpoint.

**Required:**

- `WS /containers/{name}/logs/stream` for real-time tailing.
- Reuses the same allowlist / token model as `/shell/stream`.

**Source:** UI brief proposed work; no formal owner yet.
