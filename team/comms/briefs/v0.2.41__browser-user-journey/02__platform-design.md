---
title: "Browser User-Journey — 02 — Platform design"
version: v0.2.41
date: 2026-05-26
audience: Architect / Dev / QA / DevOps picking up the next slice
status: PROPOSED — substrate (01 Part A) + tool-API framework (01 Part B) are ready to host this design
---

# 02 — Platform design

`01` describes a ready substrate and a ready tool-API framework. This file
designs **`sg browser user-journey`** on top of both: a conductor that fans out
worker containers, a vault-resident journey/run model adopted from the qa pack,
and two TUIs driven by one tool-API provider.

Diagrams for everything here are in `03__architecture-flows-ux.md`.

---

## 1. The vault layout (adopted from the qa pack, renamed)

A user-journey vault is a `sgit`-versioned tree the conductor interprets. Same
shape as `v0.2.19__qa-vault-app/02` §1, with `scenarios/` → `journeys/`:

```
uj-vault/
├── .vault-settings.json              # app id = "user-journey"
├── journeys/                         # INPUT — versioned, reviewable, branchable
│   ├── login-happy-path.json         # a Schema__Journey__Definition
│   ├── browse-catalogue.json
│   └── vault-actions/                # "open a vault and do N actions"
│       ├── 01__open.json
│       └── 02__edit-and-save.json
├── suites/                           # INPUT — Schema__Suite__Definition files
│   ├── nightly-regression.json
│   └── checkout-load-500.json
├── environments/{dev,main,prod}.json
└── runs/
    └── 2026/05/26/
        └── checkout-load-500__14-02-09Z__a1b2/      # one SUITE run
            ├── suite-result.json     # Schema__Suite__Run__Result (aggregate)
            └── workers/
                └── login__00007__c3d4/
                    ├── result.json   # Schema__Journey__Result (per worker)
                    ├── screenshots/
                    └── network-log.ndjson   # this worker's mitmproxy capture
```

`journeys/` and `suites/` are the input; `runs/` is the output, written back into
the same vault — every run is one `sgit log` away. **The audit trail is free.**

---

## 2. Where things run

- **Conductor** — a **dedicated container** on the stack's `vault-net`, added by
  this spec's compose (the substrate compose is unchanged). Owns suites; fans out
  workers via the **Docker socket**; reads journeys/suites from the vault; writes
  `runs/`; pulls per-run capture from mitmproxy; exposes the suite API.
- **Workers** — launched **on demand** by the conductor, N per suite entry, in
  waves of `concurrency`. Each is one journey execution. Not in the compose.
- **mitmproxy / vault / host-plane** — the shared substrate services from `01`.
- The substrate's shared `sg-playwright` service stays available for ad-hoc
  single runs; the **fan-out path does not use it** (see §4 — workers bundle their
  own browser for true concurrency).

---

## 3. The worker — a dedicated journey-runner image

The key evolution from the qa "one runner → shared service" model: for load we
need N concurrent browsers, and one shared `sg-playwright` service is a
bottleneck (its hard-timeout watchdog would kill in-flight peers). So:

**Worker image** (`diniscruz/sg-journey-runner`, NEW):

- **FROM** the Playwright base (`mcr.microsoft.com/playwright/python:v1.58.0-noble`)
  — Chromium present.
- **pip-installs this repo's packages** so it can `import` the Playwright **core**
  (`Playwright__Service`) and the user-journey app code (journey schemas,
  evaluator, vault client). It runs the browser **in-process via the reused
  core** — `Step__Executor` stays the only `page.*` site, so the boundary holds
  **and** the substrate `sg-playwright` *service/image* stays generic (no journey
  code added to it — the qa "substrate vs app" discipline).

**Worker run loop** (per container):

1. Read the journey (`Schema__Journey__Definition`) — inline via env for small
   ones, or by `{conductor_url, journey_id}` for large ones.
2. Build a `Schema__Sequence__Request`: the journey `steps` + synthetic
   `wait_for`/`get_content` for DOM assertions; inject `X-SG-Run-Id` into
   `extra_http_headers`.
3. Run it in-process through mitmproxy (`SG_PLAYWRIGHT__DEFAULT_PROXY_URL`).
4. Pull this run's flows: `GET /capture/network-log/{run_id}` (slice #4).
5. Evaluate assertions (stateless evaluator).
6. Write `runs/.../workers/<run_id>/result.json` + artefacts into the vault; POST
   a terminal status to the conductor; exit.

**Custom-journey escape hatch:** a journey type that the 16-verb language can't
express (rich vault actions) is just a **different worker image** — the platform
runs containers and aggregates; it is journey-agnostic. The `journey-runner`
image covers the declarative common case.

---

## 4. Schemas (Type_Safe, one class per file)

We **adopt the qa-vault-app schema family**, renamed `QA → Journey`, and add the
suite/worker layer the qa pack didn't have.

### 4.1 Journey + assertions (converged with `v0.2.19__qa-vault-app/02` §3)

```python
class Schema__Journey__Definition(Type_Safe):       # was Schema__QA__Scenario
    journey_id     : Safe_Str__Id
    target_url     : Safe_Str__Url
    environment    : Safe_Str__Key
    browser_config : Schema__Browser__Config = None  # reused from the substrate package
    capture_config : Schema__Capture__Config
    steps          : List[dict]                       # parsed by Enum__Step__Action
    assertions     : List[dict]                       # parsed by Enum__Assertion__Type
    tags           : List[Safe_Str__Key]

class Schema__Journey__Result(Type_Safe):           # was Schema__QA__Run__Result
    run_id            : Safe_Str__Id                  # YYYY-MM-DDTHH-mm-ssZ__{journey_id}__{uuid8}
    journey_id        : Safe_Str__Id
    status            : Enum__Journey__Run__Status    # PASSED | FAILED | ERROR
    sequence_response : dict
    assertion_results : List[Schema__Journey__Assertion__Result]
    started_at        : Timestamp_Now
    ended_at          : Timestamp_Now
    network_log_ref   : Schema__Artefact__Ref = None
```

Assertion vocabulary = the qa pack's 7 types, **verbatim**
(`Enum__Assertion__Type`: `URL_CONTAINS, URL_EQUALS, SELECTOR_VISIBLE,
SELECTOR_TEXT_EQUALS, SELECTOR_TEXT_CONTAINS, STATUS_CODE_EQUALS,
HTTP_HEADER_PRESENT`) + the stateless `Journey__Assertion__Evaluator` (no `page.*`,
no network, unit-testable on synthetic inputs).

### 4.2 Suites (NEW — the fan-out layer)

```python
class Schema__Suite__Entry(Type_Safe):
    worker_image : Safe_Str__Id                       # default diniscruz/sg-journey-runner
    journey_id   : Safe_Str__Id                       # which journey in the vault
    env          : Schema__Suite__Entry__Env          # per-run params (typed)
    count        : Safe_Int                           # how many copies  → LOAD
    concurrency  : Safe_Int                            # max in-flight at once

class Schema__Suite__Definition(Type_Safe):
    suite_id : Safe_Str__Id
    entries  : List[Schema__Suite__Entry]
    tags     : List[Safe_Str__Key]

class Schema__Suite__Run__Status(Type_Safe):
    suite_run_id : Safe_Str__Id
    state        : Enum__Suite__Run__State            # PENDING|RUNNING|DONE|FAILED|STOPPED
    counts       : Schema__Suite__Counts              # pending/running/passed/failed/error
    workers      : List[Schema__Worker__Status]
    aggregates   : Schema__Suite__Aggregates          # latency p50/p95/p99, throughput, flow totals
```

### 4.3 Stack lifecycle (mandated by the spec contract)

`Schema__User_Journey__{Create__Request,Create__Response,Info,List,Delete__Response}`
— `create` accepts `--interceptor-script` and a `--vault-key`.

---

## 5. The operator surface — one provider, three faces

The **same** `User_Journey__Tui_Api__Provider` (a `Tui_Api__Provider` subclass)
backs the CLI passthroughs, the cockpit buttons, **and** the chat cockpit's LLM
tools. Its `dispatch()` calls a `Conductor__Client` (HTTP → the on-box conductor).

### 5.1 Provider actions (each gets JSON-schema input + scope + dry-run)

| Action | Mutating? | Maps to conductor |
|---|---|---|
| `list_suites` / `get_suite` | no | `GET /suites`, `GET /suites/{id}` |
| `start_suite` | **yes** | `POST /suites` (gated + audited) |
| `scale_suite` | **yes (cost!)** | `PATCH /suites/{id}` count/concurrency (dry-run preview shows projected container count) |
| `stop_suite` | **yes** | `POST /suites/{id}/stop` |
| `get_flows` | no | `GET /suites/{id}/flows` (per-run capture) |
| `get_worker_logs` | no | host-plane `/pods/{name}/logs` |
| `get_interceptor` | no | mitmproxy `/config/interceptor` |

Mutating + cost-bearing actions flow through the execution center's **dry-run →
mutation gate → audit** path (01 §B3). Scaling to 500 workers shows a preview and
requires confirm.

### 5.2 Workflows = curated grant bundles

| Workflow | Grants | Use |
|---|---|---|
| `monitor` | read-only (`list/get/flows/logs`) | safe dashboards, demos, untrusted chat |
| `operate` | + `start_suite`, `stop_suite` | run regression suites |
| `load` | + `scale_suite` | load testing (cost-aware; dry-run on by default) |

The chat cockpit launches with a workflow, so the LLM only ever sees the tools
that workflow grants — "the model never picks tools; a workflow curates grants."

### 5.3 The two API layers (don't conflate)

| Layer | Runs | Owns | Consumers |
|---|---|---|---|
| Control-plane spec API `/api/specs/user-journey` | wherever `sg` runs | **stack** lifecycle (create/info/list/delete) | `sg` CLI, dashboard |
| Conductor API (on the EC2) | conductor container | **suite** lifecycle + monitoring + fan-out | the TUIs + chat (direct, `public_ip`+token), provider dispatch |

### 5.4 CLI (deliberately thin) — `sg browser user-journey …`

Stack verbs from `Spec__CLI__Builder` + passthroughs:
`create [--interceptor-script F] [--vault-key K]` · `suite start <stack> --file s.json` ·
`suite stop <stack>` · `status <stack> [--json]` · `flows <stack>` ·
**`tui <stack>`** (the cockpit) · **`chat <stack> [--workflow monitor|operate|load]`**.

CI = `create` → `suite start --file nightly-regression.json` → poll `status --json`
→ gate → `delete`. No orchestration logic in the CLI.

### 5.5 The two TUIs

- **Cockpit** (`User_Journey__Cockpit__Screen`, clones the Textual `App` layout
  from `Bedrock__Chat__Screen`): live worker grid (one cell per worker — raise
  `count`, watch it grow), aggregates (pass/fail, p50/p95/p99), a live flow feed,
  per-worker drill-down. Buttons invoke the provider through the execution center.
- **Chat cockpit**: the same screen + a chat panel using `send_turn_agentic` +
  `Chat__Tool__Builder`. "Run the checkout journey 200× and tell me the p95" → tool
  calls. Tool-call cards (`Chat__Tool_Calls`) show each `start_suite` / `get_suite`.

### 5.6 Placement — `sg browser`

New thin aggregator `sg_compute/cli/Cli__Browser.py`; `Cli__SG.py` gains one line
(`add_typer(browser_app, name='browser')`); this spec registers as `user-journey`.
`manifest.nav_group = BROWSERS` (enum value already exists). Migrating
`vnc/firefox/neko/playwright` under `sg browser` is **out of scope** here (a later
ontology slice — see §8 Q2).

---

## 6. Slice plan (dependency-ordered; mostly parallelisable)

| Slice | Deliverable | Where | Tests |
|---|---|---|---|
| **1 — per-run capture** | `GET /capture/network-log/{run_id}` + ring buffer + intercept edits | `sg_compute_specs/mitmproxy/` | local-HTTP fake (no mocks) |
| **2 — journey schemas + evaluator** | `Schema__Journey__*`, `Enum__Assertion__Type` + 7 types, stateless evaluator | new `user_journey` spec | round-trip + synthetic-input evaluation |
| **3 — suite schemas** | `Schema__Suite__*`, `Schema__Worker__Status` | new spec | round-trip + registry |
| **4 — worker image** | `sg-journey-runner` image + run loop (in-process core, vault I/O, X-SG-Run-Id) | new image + `sg_compute_specs/playwright` import | in-memory: run a journey → emit `Schema__Journey__Result` |
| **5 — conductor** | conductor image: `Suite__Runner` (socket fan-out, waves), `Result__Aggregator`, suite API | new image | fake Docker runtime; in-memory aggregation |
| **6 — spec + CLI group** | manifest, `User_Journey__Service`, `Routes__User_Journey__Stack`, `Cli__User_Journey`, `Cli__Browser` | new spec + `sg_compute/cli` | `test_manifest.py` + in-memory CRUD |
| **7 — tool-API provider + workflows** | `User_Journey__Tui_Api__Provider`, `Conductor__Client`, 3 workflows | new spec + `tui/tool_api` | execution-center dispatch (dry-run/gate/audit), in-memory chat tool-loop |
| **8 — cockpit + chat TUIs** | `User_Journey__Cockpit__Screen` + chat panel | new spec `tui/` | import-guarded Textual tests |
| **9 — e2e + load** | deploy-via-pytest: create → suite (with/without interceptor) → assert runs in vault → delete; then concurrency fan-out + percentiles | `tests/deploy/` | gated on AWS + Chromium |

Slices 1–3 and 6–8 need no AWS and parallelise. 1 is the shared prerequisite. 4–5
are the fan-out core. 9 is the gated integration + load proof.

---

## 7. What this platform does NOT add (boundaries preserved)

- **No `page.*`** outside `Step__Executor` (workers use the reused core; conductor/
  provider/TUIs are HTTP/orchestration only).
- **No journey code in the substrate `sg-playwright` service/image** — it stays
  generic; journey logic lives in the worker/`user_journey` spec.
- **No new sink writer** — artefacts via the substrate's `Artefact__Writer` / vault.
- **No boto3** — `osbot-aws` + `EC2__Platform`.
- **No widening of the JS allowlist** — `evaluate` stays server-side allowlist-gated.
- **No bespoke tool/chat plumbing** — reuse `Chat__Engine` + the execution center.

---

## 8. Open questions

| # | Question | Recommended answer |
|---|---|---|
| Q1 | New spec, or a `vault-app` mode? | **New `user-journey` spec** that *deploys the vault-app substrate + a conductor*. The synergy is huge but the conductor/fan-out/TUI is its own concern. (Human chose "new spec".) |
| Q2 | How far does `sg browser` grouping go? | **Group + nest `user-journey` only.** Migrating existing browser specs is a later ontology slice — and it tensions with the Librarian's ontology proposal (which currently opposes CLI super-grouping). Needs Librarian + human ratification. |
| Q3 | Worker = reuse Playwright image (cmd override) or dedicated runner image? | **Dedicated `sg-journey-runner` image** (FROM the Playwright base, imports the core as a library). Keeps the substrate generic; gives per-container concurrency. |
| Q4 | Conductor fan-out via `/pods` or Docker socket? | **Docker socket** — `/pods` can't override command/limits. Same access host-plane already has. |
| Q5 | Where does journey/worker code live — sibling repo (qa Q1) or this repo? | **This repo**, as the `user_journey` spec — the human wants it as a first-class `sg` capability, not a sibling service. (Divergence from the qa pack's sibling-repo lean; noted intentionally.) |
| Q6 | Hot-swap interceptors on a live stack? | **No (v1).** mitmproxy hot-reload (`PUT /config/interceptor`) is unbuilt; "with/without" = create-time selection per ephemeral stack. |
| Q7 | Conductor + worker = new CI images? | **Yes — two new images published to Docker Hub (NOT ECR):** `diniscruz/sg-journey-conductor` (lightweight: python + docker CLI) and `diniscruz/sg-journey-runner` (FROM the Playwright base). Mirror the host-control Docker-Hub build/publish flow (GH Actions → `docker push diniscruz/…`). Public images → no pull-time auth on the EC2. |
| Q8 | Run-id / suite-run-id format? | `YYYY-MM-DDTHH-mm-ssZ__{id}__{uuid8}` — sortable + greppable in the vault tree; `Safe_Str__Id` validates. |

---

## 9. References

- `00__README.md` · `01__substrate-contract.md` · `03__architecture-flows-ux.md`
- Architect plan: `team/roles/architect/reviews/05/26/v0.2.41__browser-user-journey-platform__plan.md`
- The design we extend: `team/comms/briefs/v0.2.19__qa-vault-app/02__qa-app-design.md`
- Playwright API agent guide: `library/guides/v0.2.6__playwright-api-for-agents.md`

---

*Next: open `03__architecture-flows-ux.md` for the drawn architecture, flows, and UX. Then start slice 1 (per-run capture) and slice 2 (schemas) in parallel.*
