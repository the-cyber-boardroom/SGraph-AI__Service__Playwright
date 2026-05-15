---
title: "QA Vault-App — 02 — Design of the QA app"
version: v0.2.6
date: 2026-05-15
audience: Architect / Dev / QA picking up the next slice
status: PROPOSED — does not exist yet; substrate (file 01) is ready to host it
---

# 02 — Design of the QA app

The substrate (`01__what-exists-today.md`) gives us a deploy command, a
Playwright REST API on `:11024`, mitmproxy capturing 100% of browser
traffic, a vault on `:443`, and a one-secret auth model. The QA vault-app
**lives inside the vault** as a sgit-cloned repo, drives the Playwright
service to run scenarios, and writes results back into the vault.

This file proposes the QA app's design, schemas, and a slice plan.
It does **not** propose new code in `sg_compute_specs/playwright/` — per
the v2 delta reframe, QA-specific code stays out of this repo.

---

## 1. What "QA app in a vault" actually means

A vault is a `sgit`-versioned directory tree served by `sg-send-vault`. A
**vault-app** is a vault with extra structure that an external runtime
(scheduler, browser, agent) interprets. For QA:

```
qa-vault/
├── .vault-settings.json            # auth, layout version, app id = "qa"
├── README.md                       # human entry point
├── scenarios/                      # versioned, sgit-tracked
│   ├── login-happy-path.json       # one scenario per file
│   ├── checkout-paywall.json
│   └── nightly-smoke/              # group folders are fine
│       ├── 01__home.json
│       └── 02__pricing.json
├── environments/
│   ├── dev.json                    # base_url, header overrides, viewport, …
│   ├── main.json
│   └── prod.json
└── runs/
    └── 2026/05/15/
        └── login-happy-path__03-21-44Z__b8f2/
            ├── result.json         # Schema__QA__Run__Result
            ├── screenshots/
            │   ├── 01__navigate.png
            │   └── 04__after-click.png
            ├── network-log.ndjson   # mitmproxy capture for this run
            └── notes.md             # optional human annotation
```

Three things make this a "vault-app" rather than a folder full of JSON:

1. **`scenarios/` are the input** — git-versioned, reviewable, branchable.
2. **`runs/` are the output** — written back into the same vault, so the
   history of every scenario across every run is one `sgit log` away.
3. **The runtime is `sg-playwright`** — the QA app holds no browser logic;
   it composes Playwright API calls.

---

## 2. Architecture — where the QA app's code runs

Three reasonable homes for the QA runner. The pack recommends (a):

### (a) Runs on the same EC2, alongside the vault and Playwright service. **Recommended.**

A small Python service inside its own container on the same `vault-net`,
reading the scenario from the vault (HTTP via sg-send-vault) and POSTing to
`http://sg-playwright:8000/sequence/execute` (internal). Latency is zero
hops; the vault and playwright are already on this host; auth is the
shared access token.

Compose addition (proposed; sketch — final shape decided in slice 1):

```yaml
  qa-runner:                      # NEW container — the QA vault-app's runtime
    image: <tbd>/sg-qa-runner:latest
    environment:
      QA_VAULT_KEY:             ${QA_VAULT_KEY}
      QA_SCHEDULE:              "*/5 * * * *"          # or "manual" / "watch"
      SGRAPH_SEND_URL:          http://sg-send-vault:8080      # or https:8443 over TLS
      SG_PLAYWRIGHT_URL:        http://sg-playwright:8000
      FAST_API__AUTH__API_KEY__VALUE: ${FAST_API__AUTH__API_KEY__VALUE}
    networks:
      - vault-net
    depends_on:
      - sg-send-vault
      - sg-playwright
    restart: unless-stopped
```

Pros: zero network egress for scenarios + runs; same auth scope; fits the
existing compose pattern; isolated container.

### (b) Runs as a worker inside the sg-send-vault container.

Pros: even tighter — no separate container, runs inside the vault process.
Cons: couples the QA runner's lifecycle to the vault's; changes to one
require deploying the other. **Rejected.**

### (c) Runs outside the EC2 (laptop, CI, Lambda).

Pros: no compose changes; scheduling is external. Cons: every scenario
read and every result write crosses the public internet; auth surface is
broader. **Rejected for the default; legitimate for ad-hoc dev runs.**

---

## 3. Schemas — what lives in the QA vault-app

All `Type_Safe`, one class per file, no Pydantic, no Literals. These live
in the QA vault-app's own repo (a sibling, not in this one), so paths
below are package-relative.

### 3.1 The scenario

```python
class Schema__QA__Scenario(Type_Safe):
    scenario_id    : Safe_Str__Id                  # unique within the vault
    target_url     : Safe_Str__Url
    environment    : Safe_Str__Key                 # 'dev' | 'main' | 'prod' — free-form (envs come from vault)
    browser_config : Schema__Browser__Config = None  # reuses the playwright service's schema
    capture_config : Schema__Capture__Config         # required; specifies where artefacts land
    steps          : List[dict]                    # one entry per Enum__Step__Action (parsed by playwright)
    assertions     : List[dict]                    # heterogeneous; parsed by Enum__Assertion__Type
    tags           : List[Safe_Str__Key]
    notes          : Safe_Str__Text
```

A scenario is **declarative** — no JS in scenario files except via the
existing `evaluate` step, which is allowlist-gated server-side.

### 3.2 The run result

```python
class Schema__QA__Run__Result(Type_Safe):
    run_id            : Safe_Str__Id               # YYYY-MM-DDTHH-mm-ssZ__{scenario_id}__{uuid8}
    scenario_id       : Safe_Str__Id
    environment       : Safe_Str__Key
    status            : Enum__QA__Run__Status      # PASSED | FAILED | ERROR
    sequence_response : dict                       # the playwright service's response, verbatim
    assertion_results : List[Schema__QA__Assertion__Result]
    started_at        : Timestamp_Now
    ended_at          : Timestamp_Now
    network_log_ref   : Schema__Artefact__Ref = None   # populated when the mitmproxy slice (§5 below) lands
```

### 3.3 The assertion vocabulary

Mirror the step vocabulary — discriminator enum + per-type subclass +
registry:

| `Enum__Assertion__Type` value | Schema                                | What |
|---|---|---|
| `URL_CONTAINS`           | `Schema__QA__Assertion__Url_Contains`            | After the sequence, current URL contains the given substring. |
| `URL_EQUALS`             | `Schema__QA__Assertion__Url_Equals`              | Exact URL match. |
| `SELECTOR_VISIBLE`       | `Schema__QA__Assertion__Selector_Visible`        | An element matching the selector is in the viewport. |
| `SELECTOR_TEXT_EQUALS`   | `Schema__QA__Assertion__Selector_Text_Equals`    | Selector's text content equals the expected string. |
| `SELECTOR_TEXT_CONTAINS` | `Schema__QA__Assertion__Selector_Text_Contains`  | Selector's text content contains the expected substring. |
| `STATUS_CODE_EQUALS`     | `Schema__QA__Assertion__Status_Code_Equals`      | A specific URL in the network log returned the expected HTTP status. |
| `HTTP_HEADER_PRESENT`    | `Schema__QA__Assertion__Http_Header_Present`     | A specific URL's response carried the expected header. |

Per-result envelope:

```python
class Schema__QA__Assertion__Result(Type_Safe):
    assertion_id  : Safe_Str__Id
    type          : Enum__Assertion__Type
    status        : Enum__Assertion__Status      # PASSED | FAILED | ERROR | SKIPPED
    expected      : Safe_Str__Text               # human-readable
    actual        : Safe_Str__Text               # human-readable
    duration_ms   : int
    error_message : Safe_Str__Text = None
```

**Key design point**: assertions that need DOM access (`SELECTOR_VISIBLE`,
`SELECTOR_TEXT_*`) are implemented by **appending synthetic
`Schema__Step__Wait_For` / `Schema__Step__Get_Content` to the sequence**
*before* it hits Playwright. The QA app never touches `page.*` directly —
that's `Step__Executor`'s sole privilege, preserved end to end.
Assertions that don't need DOM (URL / status / header) read from the
returned `Schema__Sequence__Response` and the per-run network log
(slice 4 below).

---

## 4. The Assertion Evaluator — pure logic over typed inputs

```python
class QA__Assertion__Evaluator:
    def evaluate(self, scenario, sequence_response, network_log) -> List[Schema__QA__Assertion__Result]:
        ...
```

- Stateless, no `page.*` access, no network calls.
- One method per `Enum__Assertion__Type` (dispatch via the registry).
- Returns one `Schema__QA__Assertion__Result` per assertion in the
  scenario; never raises out of the evaluator (errors become `ERROR`
  results with a populated `error_message`).
- Unit-testable in-memory with synthetic `Schema__Sequence__Response` +
  synthetic network logs — no Chromium needed for the URL / status /
  header types.

The evaluator is the **only QA-specific logic that runs per-step**. Everything
else — fetching the scenario, calling Playwright, writing the result back
to the vault — is plumbing.

---

## 5. The per-run network log — the one substrate slice this needs

The capture exists today (mitmproxy NDJSON to stdout). What's missing is
**per-run addressability**: the QA runner needs to retrieve a run's
network log keyed by `run_id`.

Proposed shape (the only substrate change this brief requests):

1. The QA runner injects `X-SG-Run-Id: <run_id>` into every browser
   request via the existing `Schema__Session__Credentials.extra_http_headers`
   channel. (No code change in the playwright service — this just uses an
   existing field.)
2. The mitmproxy intercept script (in the `agent_mitmproxy` image) groups
   captured flows by the `X-SG-Run-Id` request header, keeping the last N
   minutes in an in-memory ring buffer.
3. `Fast_API__Agent_Mitmproxy` (the admin FastAPI on agent-mitmproxy)
   gets a new endpoint `GET /capture/network-log/{run_id}` returning the
   NDJSON-bytes for that run.
4. The QA runner fetches that log post-run, writes it into the run folder
   in the vault as `network-log.ndjson`, and sets `network_log_ref` on the
   result.

This is the **only piece of substrate code this brief requests**. It
belongs in the `agent_mitmproxy` spec (already in this repo), not in the
QA vault-app. Estimated ~80 lines + a test against the existing
`Routes__Web`-style local-HTTP fake.

---

## 6. Slice plan for the QA vault-app

All slices below produce code in the **QA vault-app's own repo** (a sibling
`SGraph-AI__Service__QA-Util` or similar), except slice 4 which is the
substrate addition described above.

### Slice 1 — Scenario / result schemas + registry

```
qa_vault_app/
  schemas/
    Schema__QA__Scenario.py
    Schema__QA__Run__Result.py
    enums/
      Enum__Assertion__Type.py
      Enum__Assertion__Status.py
      Enum__QA__Run__Status.py
    assertions/
      Schema__QA__Assertion__Base.py
      Schema__QA__Assertion__Url_Contains.py
      ... (7 files, one per assertion type)
    results/
      Schema__QA__Assertion__Result.py
  dispatcher/
    assertion_schema_registry.py
```

Tests: in-memory round-trip every schema; registry parses 7 example dicts;
rejection of unknown assertion type.

### Slice 2 — Assertion Evaluator (URL / status / header — no DOM)

```
qa_vault_app/service/QA__Assertion__Evaluator.py
```

Tests: `URL_CONTAINS`, `URL_EQUALS`, `STATUS_CODE_EQUALS`, `HTTP_HEADER_PRESENT`
against synthetic `Schema__Sequence__Response` + synthetic network logs.
No Chromium needed.

### Slice 3 — Scenario Runner + Vault client + Playwright client

```
qa_vault_app/service/
  QA__Vault__Client.py            # talks to sg-send-vault for scenarios + runs
  QA__Playwright__Client.py        # thin wrapper over POST /sequence/execute
  QA__Scenario__Runner.py          # composes the above + the evaluator
```

The runner:

1. Reads `scenarios/<id>.json` from the vault.
2. Builds `Schema__Sequence__Request` — `steps` from the scenario, plus
   synthetic `Wait_For` / `Get_Content` for DOM assertions.
3. Injects `X-SG-Run-Id` into the request.
4. Calls Playwright; awaits the response.
5. Pulls the per-run network log from mitmproxy (slice 5).
6. Hands all three to the evaluator.
7. Writes `runs/<date>/<run_id>/result.json` + artefacts into the vault.

Tests: in-memory composition; the runner against fake vault + fake playwright
+ fake network-log provider. No real network.

### Slice 4 — `agent_mitmproxy` per-run capture endpoint (substrate slice)

This is the **one slice in this branch's repo**. Files:

```
sg_compute_specs/mitmproxy/api/routes/Routes__Capture.py            # NEW
sg_compute_specs/mitmproxy/service/Capture__Ring_Buffer.py          # NEW
sg_compute_specs/mitmproxy/docker/images/agent_mitmproxy/...        # intercept script edits
```

`GET /capture/network-log/{run_id}` → NDJSON of the flows tagged with that
`X-SG-Run-Id`. Ring buffer is in-memory (keep last 24h of runs, or N MB).
Tests: real local HTTPServer fake (same pattern as `test_Routes__Web`).

### Slice 5 — End-to-end deploy test against a live vault-app stack

A `tests/integration/test_qa_vault_app_e2e.py` that:

1. `sp vault-app create --with-playwright --wait` against a CI-only short-
   lived EC2.
2. Clones a known QA vault via `--seed-vault-keys`.
3. Triggers a known-good scenario through the QA runner (HTTP).
4. Asserts: the result JSON appears in `runs/<date>/<run_id>/`, the network
   log is non-empty, all assertions returned `PASSED`.
5. `sp vault-app delete` regardless of outcome.

### Slice 6 — Schedule / watch modes (post-MVP)

Not part of the MVP. The runner exposes a `/run/<scenario_id>` HTTP
trigger; whether that's invoked by cron-inside-the-container or by an
out-of-EC2 GitHub Actions scheduler is the deploy operator's choice.

---

## 7. What the QA app does NOT need from this repo

By design, these stay out of `sg_compute_specs/`:

- `Schema__QA__*` — all in the QA app's repo.
- `Routes__QA` — no QA endpoint on the playwright service.
- `Assertion__Evaluator` — in the QA app's service tree.
- A QA-scheduler spec — explicitly dropped.
- Daily-summary / report generators — QA app post-MVP, not substrate.

The only thing the QA app asks of this repo is slice 4 (per-run mitmproxy
capture). Everything else already exists.

---

## 8. Open questions (extracted from v1 §6, updated for v2 reality)

| # | Question | Recommended answer |
|---|---|---|
| Q1 | Where does the QA vault-app's code live? | New repo `SGraph-AI__Service__QA-Util` (or similar). Don't add a `sg_compute_specs/qa/` here — keeps the substrate clean and the QA app independently versioned. |
| Q2 | Is `IFRAME_INJECTION` execution mode in scope? | **No.** Closed via v2 delta. The substrate has only real-browser; iframe-mode is a *client-side* concern of a future UI, not the QA runner. |
| Q3 | Per-run network log — fetch via mitmproxy admin endpoint, or push-style? | **Pull** via the new `GET /capture/network-log/{run_id}` (slice 4). Simpler; matches the existing Routes__Web pattern; no message-bus dependency. |
| Q4 | Run-id format — opaque or structured? | Structured by convention: `YYYY-MM-DDTHH-mm-ssZ__{scenario_id}__{uuid8}`. Keeps the vault tree sortable + greppable. Validated by `Safe_Str__Id` only — the QA runner enforces the shape. |
| Q5 | Idempotency on re-runs of the same run-id? | The runner refuses to overwrite an existing `runs/<...>/result.json`. Re-runs require a new run-id (mint a fresh uuid8). |
| Q6 | Free-form assertions vs the typed registry? | **Typed only.** Free-form raw-dict assertions violate the Type_Safe rule and bypass schema validation. Anything not on the `Enum__Assertion__Type` registry is rejected at parse time. New assertion types land via the registry, not as escape hatches. |
| Q7 | Should the QA runner's container go in the vault-app compose template? | Not by default — keeps the substrate generic. Provide a `--with-qa-runner` create flag in the QA vault-app's own CLI (which composes ON TOP of `sp vault-app create`), so the substrate compose template stays clean. |
| Q8 | What schedules the runner? | MVP: manual trigger via the QA runner's HTTP surface. Post-MVP: ordinary cron inside the container OR GitHub Actions hitting the runner. Schedulers are not a substrate concern. |

---

## 9. References

- `00__README.md` — this pack's index + the status table.
- `01__what-exists-today.md` — the substrate surface this design consumes.
- `library/guides/v0.2.6__playwright-api-for-agents.md` — the Playwright
  API reference any agent (including the QA runner) reads to drive `/sequence/execute`.
- `team/comms/briefs/v0.2.6__vault-to-playwright-api.md` — internal vs external URLs + auth.
- `team/humans/dinis_cruz/claude-code-web/05/13/21/v0.2.6__arch-plan__qa-service.md` — v1 (embedded QA-in-this-repo); superseded.
- `team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md` — v2 reframe; the substrate part shipped, the QA-vault part is this file.

---

*Next: a dev sits down with this file + `library/guides/v0.2.6__playwright-api-for-agents.md` and a fresh `sp vault-app create --with-playwright --wait`. Slice 1 (schemas) and slice 4 (per-run mitmproxy capture) are independent and parallelisable.*
