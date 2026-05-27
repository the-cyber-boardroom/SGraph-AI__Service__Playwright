# user-journey — Reality Index

**Domain:** `user-journey/` | **Last updated:** 2026-05-27 | **Maintained by:** Dev (landing) → Librarian (verify)
**Code-source basis:** `sg_compute_specs/user_journey/` + `sgraph_ai_service_playwright__cli/tui/tool_api/core/user_journey/` + `sgraph_ai_service_playwright__cli/tui/screens/user_journey/` (branch `claude/browser-automation-cli-architect-xgULF`, **not yet merged to `dev`**).

The user-journey tier turns one declarative journey into a fan-out **suite** of browser workers, run and monitored by an on-box **conductor**, and driven from a CLI, two cockpit TUIs, or an LLM. It **reuses** the Playwright core (sequence execution) and the agent-mitmproxy per-run capture rather than re-implementing them — `Step__Executor` stays the only caller of `page.*`.

---

## EXISTS (code-verified, branch only)

### Journey + worker (one run)

- `core/schemas/journey/Schema__Journey__Definition` — one declarative journey (adopts the qa-vault-app `Schema__QA__Scenario` shape: `target_url`, `steps`, `assertions`, reused `Schema__Browser__Config` / `Schema__Capture__Config`).
- `core/worker/Journey__Sequence__Builder` — journey → a Playwright `Schema__Sequence__Request`, injecting **`X-SG-Run-Id`** into `extra_http_headers` so the mitmproxy per-run capture can attribute flows.
- `core/worker/Journey__Worker` — `run()` is the integration path (build sequence → `playwright_service.execute_sequence` → pull this run's flows → evaluate → `Schema__Journey__Result`); `derive_status` / `assemble_result` are pure + unit-tested.
- `core/evaluator/Journey__Assertion__Evaluator` (+ assertion schema registry under `core/dispatcher/`) — verdicts over the sequence response + network log.
- `core/worker/Journey__Worker__Entrypoint` — the container CMD. `run_id_from_env` / `journey_from_env` are pure (read `SG_UJ__RUN_ID` / `SG_UJ__JOURNEY_JSON`); `main()` is the gated Chromium shim (`Playwright__Service()`).

### Suite + conductor (the fan-out)

- `core/schemas/suite/Schema__Suite__Definition` + `Schema__Suite__Entry` (image × journey × `count` × `concurrency`) — raising `count` = more load.
- `core/conductor/Suite__Runner` — pure planner: expand each entry into per-replica `Schema__Worker__Spec`s, chunk into launch waves of `concurrency`. `plan(...)` accepts an optional `journeys` map → attaches the full journey to each spec.
- `core/conductor/Suite__Service` — suite lifecycle (plan → launch waves via the runtime port → report → stop → scale).
- `core/conductor/Result__Aggregator` — worker results → `Schema__Suite__Counts` + `Schema__Suite__Aggregates` (pass/fail/error, latency p50/p95/p99, flows total/blocked).
- `core/conductor/api/Fast_API__Conductor` + `api/routes/Routes__Suites` — the on-box suite HTTP API (start / get / scale / stop / flows).
- `core/clients/Conductor__Client` — typed HTTP client; `parse_status` is pure + unit-tested, the HTTP calls are gated.

### Worker runtime (the launch port)

- `core/conductor/Worker__Runtime` — abstract launch port (`launch` / `stop`).
- `core/conductor/Worker__Runtime__InMemory` — default/test backend; records specs, returns RUNNING without Docker.
- `core/conductor/Worker__Runtime__Docker` — real `docker run`. `docker_run_args` is pure (argv only), injecting the run identity + journey as `SG_UJ__RUN_ID` / `SG_UJ__WORKER_ID` / `SG_UJ__JOURNEY_ID` / `SG_UJ__ENVIRONMENT` / **`SG_UJ__JOURNEY_JSON`**; `run_docker` is the single subprocess seam (tests subclass it). `docker_available()` gates callers. Container naming matches the in-memory backend.

**Journey delivery = env-JSON** (decided 2026-05-27): the conductor serialises the journey into `SG_UJ__JOURNEY_JSON` at launch; the worker is fully self-contained (no journey store, no conductor callback). Verified round-trip: `plan(journeys)` → `spec.journey` → `SG_UJ__JOURNEY_JSON` → `journey_from_env` → `Schema__Journey__Definition`.

### Tool-API provider + workflows (the gated "talk to the tools" seam)

- `tui/tool_api/core/user_journey/User_Journey__Tui_Api__Provider` — slug `browser.user-journey`; actions `uj.status` / `uj.flows` (READ_ONLY), `uj.start` / `uj.stop` (WRITE), `uj.scale` (DESTRUCTIVE). No gating of its own — the `Tui_Api__Execution_Center` gates WRITE/DESTRUCTIVE (dry-run + mutation gate + audit); `dispatch()` routes through `Conductor__Client`.
- `tui/tool_api/core/user_journey/User_Journey__Workflows` — `monitor` (read-only) < `operate` (+ start/stop) < `load` (+ scale) grant bundles. The model only ever sees the chosen workflow's actions (decision #10).
- `tui/tool_api/core/user_journey/User_Journey__Chat__Tools` — neutral chat-tools bridge (workflow → granted actions → `Schema__Chat__Tool` + name_map).

### Cockpit + chat TUIs

- `tui/render/User_Journey__Cockpit__Render` (in the **spec**, pure) — suite snapshot → worker-grid glyphs (`✓ ✗ ⠿ · ! ■`), header, aggregates line.
- `tui/screens/user_journey/User_Journey__Cockpit__Screen` (cli) — thin `Tui__App` subclass; `body_markup()` (fetch + render) is unit-tested headless, `populate()` is the only Textual-bound glue. `r` refreshes; `refresh_seconds` polls.
- `tui/screens/user_journey/User_Journey__Chat__Launcher` (cli) — `prepare()` builds a workflow-scoped Bedrock `tool_config` + execution center + grants (verifiable: driving `center.execute(...)` runs the whole chat dispatch path with no LLM); `launch()` mirrors the Bedrock chat `run_tui`.

### CLI surface — `sg user-journey` (alias `uj`)

Mounted in `sg_compute/cli/Cli__SG.py` as a top-level peer surface.

| Command | Does |
|---------|------|
| `sg user-journey status <run-id>` | Cockpit snapshot (worker grid + aggregates); `--json` |
| `sg user-journey scale <run-id> <count> <concurrency>` | Resize a running suite; `--json` |
| `sg user-journey stop <run-id>` | Stop a running suite; `--json` |
| `sg user-journey cockpit <run-id>` | Live Textual cockpit (lazy import, interactive) |
| `sg user-journey chat [--workflow monitor\|operate\|load]` | Conversational cockpit; LLM drives via the granted workflow tools (lazy) |

`status` / `scale` / `stop` go through `Conductor__Client` and are CliRunner-tested via the `_client_factory` seam; `cockpit` / `chat` lazy-import the cli TUI so the spec never statically imports the cli package.

### Tests

~128 tests across the three code areas — all pure / in-memory, **no mocks, no patches**. The grant gate, workflow scoping, env-JSON round-trip, planner fan-out, aggregator percentiles, cockpit render, Docker argv, and CLI verbs are all asserted in-memory.

---

## NOT BUILT (PROPOSED — does not exist yet)

Worker + conductor **Docker images**; Docker Hub **CI**; EC2 **conductor-host** provisioning/lifecycle; **deploy-via-pytest** + live load runs; the interactive Textual cockpit/chat screens exercised **live** (built, but only the pure cores are tested); vault-stored **suites by id** (`Conductor__Client.start_suite_id` exists; conductor-side resolution + a journey store are not). See `proposed/index.md`.

---

## Known gaps

- Integration paths (`Journey__Worker.run`, `Worker__Runtime__Docker.run_docker`, `Conductor__Client` HTTP, `Journey__Worker__Entrypoint.main`) are unit-tested at the contract/argv level only — the real browser / mitmproxy / Docker / HTTP legs run under the gated deploy harness, not yet executed.
- The chat cockpit `capture_client` (mitmproxy network-log client) is not wired in `Journey__Worker__Entrypoint.main` / the launcher — network assertions degrade to an empty log until the deploy harness wires it.
- This domain lives on a feature branch and is **not on `dev`**.
