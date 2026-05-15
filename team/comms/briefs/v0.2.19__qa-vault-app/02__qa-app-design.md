---
title: "QA Vault-App — 02 — Design of the QA app"
version: v0.2.19
date: 2026-05-15
audience: Architect / Dev / QA picking up the next slice
status: PROPOSED — substrate (file 01) is ready to host this design
---

# 02 — Design of the QA app

`01__substrate-contract.md` describes a ready substrate: deploy command,
TLS-fronted vault, Playwright API on port 80, mitmproxy capturing 100% of
browser traffic, single-secret auth, EC2 tags carrying the URL set. This
file proposes the QA vault-app **on top of** that substrate.

There is **one substrate item this file requests** (§5: per-run mitmproxy
addressability, ~80 lines). Everything else is QA-app-internal and
**lives in a sibling repo**, not in this one.

---

## 1. What "QA app in a vault" actually means

A vault is a `sgit`-versioned directory tree served by `sg-send-vault`. A
**vault-app** is a vault with extra structure that an external runtime
(a small companion service, in this case the QA runner) interprets.

```
qa-vault/
├── .vault-settings.json            # auth, layout version, app id = "qa"
├── README.md                       # human entry point
├── scenarios/                      # versioned, sgit-tracked
│   ├── login-happy-path.json
│   ├── checkout-paywall.json
│   └── nightly-smoke/
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

Three properties make it a *vault-app* rather than a folder full of JSON:

1. **`scenarios/` are the input** — git-versioned, reviewable, branchable.
2. **`runs/` are the output** — written back into the same vault, so the
   history of every scenario across every run is one `sgit log` away.
3. **The runtime is `sg-playwright`** — the QA app holds no browser logic;
   it composes Playwright API calls (§5 of `01__substrate-contract.md`).

---

## 2. Where the QA runner runs

Three plausible homes; the pack recommends (a):

### (a) Sibling container on the same EC2, on `vault-net`. **Recommended.**

A small Python service in its own container, reading the scenario from
the vault (HTTP via `sg-send-vault`) and POSTing to
`http://sg-playwright:8000/sequence/execute` over the docker bridge. Same
host, zero network egress for scenario/result I/O, same auth scope.

Compose addition (proposed; not in the substrate compose template — would
be added by the QA app's own deploy story, see §6 slice 6):

```yaml
  qa-runner:                      # NEW — the QA vault-app's runtime; not part of the base vault-app spec
    image: <tbd>/sg-qa-runner:latest
    environment:
      QA_VAULT_KEY:                ${QA_VAULT_KEY}
      QA_TRIGGER_MODE:             "http"                 # "http" | "watch" | "cron"
      SGRAPH_SEND_URL:             https://sg-send-vault                # internal HTTPS via service-name; cert is for the public IP, so verify=False on this internal hop
      SG_PLAYWRIGHT_URL:           http://sg-playwright:8000             # internal HTTP, port-suffixed because :8000 ≠ default :80 internally
      FAST_API__AUTH__API_KEY__VALUE: ${FAST_API__AUTH__API_KEY__VALUE}
    networks:
      - vault-net
    depends_on:
      - sg-send-vault
      - sg-playwright
    restart: unless-stopped
```

Pros: zero egress hops; same auth scope; isolated container; trivially
scalable per stack.

### (b) Inside the sg-send-vault container.

Couples the QA runner's lifecycle to the vault container's. **Rejected**
— changes to one would require redeploying the other; substrate-vs-app
boundary blurs.

### (c) Outside the EC2 (laptop, CI, Lambda).

Legitimate for ad-hoc dev runs; **not the default**. Every scenario read
and result write would cross the public internet; auth surface broadens.

---

## 3. Schemas — all in the QA app's own repo

All `Type_Safe`, one class per file, no Pydantic, no Literals. These do
**not** land in `sg_compute_specs/playwright/` — that boundary is
intentional (the v2 delta reframe).

### 3.1 Scenario

```python
class Schema__QA__Scenario(Type_Safe):
    scenario_id    : Safe_Str__Id                  # unique within the vault
    target_url     : Safe_Str__Url
    environment    : Safe_Str__Key                 # 'dev' | 'main' | 'prod' — free-form (envs come from vault)
    browser_config : Schema__Browser__Config = None  # reuses the playwright service's schema (imported from the substrate's published Python package)
    capture_config : Schema__Capture__Config         # required
    steps          : List[dict]                    # parsed by Enum__Step__Action
    assertions     : List[dict]                    # parsed by Enum__Assertion__Type (the QA app's own registry)
    tags           : List[Safe_Str__Key]
    notes          : Safe_Str__Text
```

A scenario is declarative — no JS except the existing `evaluate` step,
which is allowlist-gated server-side.

### 3.2 Run result

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
    network_log_ref   : Schema__Artefact__Ref = None   # populated after slice 4 (the one substrate follow-up)
```

### 3.3 Assertion vocabulary

Discriminator enum + per-type subclass + registry — same pattern the
substrate uses for steps:

| `Enum__Assertion__Type` | Schema                                | Reads from |
|---|---|---|
| `URL_CONTAINS`           | `Schema__QA__Assertion__Url_Contains`            | `sequence_response` (terminal URL) |
| `URL_EQUALS`             | `Schema__QA__Assertion__Url_Equals`              | `sequence_response` |
| `SELECTOR_VISIBLE`       | `Schema__QA__Assertion__Selector_Visible`        | Synthetic `Wait_For` step result (§4) |
| `SELECTOR_TEXT_EQUALS`   | `Schema__QA__Assertion__Selector_Text_Equals`    | Synthetic `Get_Content` step result |
| `SELECTOR_TEXT_CONTAINS` | `Schema__QA__Assertion__Selector_Text_Contains`  | Synthetic `Get_Content` step result |
| `STATUS_CODE_EQUALS`     | `Schema__QA__Assertion__Status_Code_Equals`      | `network_log` (mitmproxy capture, slice 4) |
| `HTTP_HEADER_PRESENT`    | `Schema__QA__Assertion__Http_Header_Present`     | `network_log` |

```python
class Schema__QA__Assertion__Result(Type_Safe):
    assertion_id  : Safe_Str__Id
    type          : Enum__Assertion__Type
    status        : Enum__Assertion__Status      # PASSED | FAILED | ERROR | SKIPPED
    expected      : Safe_Str__Text
    actual        : Safe_Str__Text
    duration_ms   : int
    error_message : Safe_Str__Text = None
```

---

## 4. The Assertion Evaluator — pure logic over typed inputs

```python
class QA__Assertion__Evaluator:
    def evaluate(self, scenario, sequence_response, network_log) -> List[Schema__QA__Assertion__Result]:
        ...
```

- Stateless. No `page.*`. No network. No mocks needed in tests.
- One method per `Enum__Assertion__Type` (dispatch via registry).
- Returns one result per assertion; never raises out (errors become
  `ERROR` results with `error_message` set).
- Unit-testable in-memory with synthetic `Schema__Sequence__Response` +
  synthetic network logs — no Chromium needed for URL / status / header
  types.

**Key architectural call**: DOM-touching assertions (`SELECTOR_VISIBLE`,
`SELECTOR_TEXT_*`) are implemented by **appending synthetic
`Schema__Step__Wait_For` / `Schema__Step__Get_Content` to the sequence
*before* it hits Playwright**. The QA app never calls `page.*` directly —
`Step__Executor` (in the substrate) remains the sole `page.*` site. The
evaluator just reads the per-step results back out.

---

## 5. The one substrate follow-up — `agent_mitmproxy` per-run capture

The capture exists today; the addressability doesn't. The QA runner needs
to retrieve a run's network log keyed by `run_id`.

**Proposed shape** (the only substrate change this pack requests):

1. The QA runner injects `X-SG-Run-Id: <run_id>` into every browser
   request via the existing
   `Schema__Session__Credentials.extra_http_headers` channel.
   **No code change in the playwright service** — uses an existing field.
2. The `agent_mitmproxy` intercept script groups captured flows by the
   `X-SG-Run-Id` request header, keeping the last N minutes in an
   in-memory ring buffer.
3. `Fast_API__Agent_Mitmproxy` (the admin FastAPI in the agent-mitmproxy
   container, reachable via `sp vault-app open mitmweb`) gets a new
   endpoint — `GET /capture/network-log/{run_id}` — returning NDJSON for
   that run.
4. The QA runner fetches the log post-run, writes it into
   `runs/<...>/network-log.ndjson`, and sets `network_log_ref` on the
   result.

Scope: ~80 lines in `sg_compute_specs/mitmproxy/`. Test against the
existing `Routes__Web`-style local-HTTP fake pattern (real sockets, no
mocks).

This is the **only substrate slice this pack asks for**. Everything else
the QA app needs already exists per `01__substrate-contract.md`.

---

## 6. Slice plan — sized for parallelism

All slices except slice 4 land in the **QA app's own repo**. Slice 4
lands here.

### Slice 1 — Scenario / result schemas + registry  (QA repo)

Schema files + assertion registry. Pure data, no behaviour.

```
qa_vault_app/schemas/
  Schema__QA__Scenario.py
  Schema__QA__Run__Result.py
  enums/{Enum__Assertion__Type, Enum__Assertion__Status, Enum__QA__Run__Status}.py
  assertions/Schema__QA__Assertion__{Base, Url_Contains, Url_Equals,
                                     Selector_Visible, Selector_Text_Equals,
                                     Selector_Text_Contains,
                                     Status_Code_Equals, Http_Header_Present}.py
  results/Schema__QA__Assertion__Result.py
qa_vault_app/dispatcher/assertion_schema_registry.py
```

Tests: round-trip every schema; registry parses 7 example dicts;
unknown-type rejection.

### Slice 2 — Assertion Evaluator  (QA repo, no DOM yet)

URL / status / header types — pure logic over typed inputs. No Chromium
needed.

### Slice 3 — Scenario Runner + Vault + Playwright clients  (QA repo)

```
qa_vault_app/service/
  QA__Vault__Client.py            # GET scenarios; PUT results & artefacts
  QA__Playwright__Client.py        # thin POST /sequence/execute wrapper
  QA__Scenario__Runner.py          # composes the above + evaluator
```

Runner flow:
1. Read `scenarios/<id>.json` from the vault.
2. Build `Schema__Sequence__Request` — scenario `steps`, plus synthetic
   `Wait_For` / `Get_Content` for DOM assertions.
3. Inject `X-SG-Run-Id` into the request's `extra_http_headers`.
4. POST to `http://sg-playwright:8000/sequence/execute` (internal).
5. Pull the per-run network log from `agent-mitmproxy` (slice 4).
6. Hand all three to the evaluator.
7. Write `runs/<date>/<run_id>/result.json` + artefacts into the vault.

Tests: in-memory composition with fake vault + fake playwright + fake
log provider. No real network.

### Slice 4 — `agent_mitmproxy` per-run capture endpoint  (THIS repo)

The one substrate slice. Files:

```
sg_compute_specs/mitmproxy/api/routes/Routes__Capture.py            # NEW
sg_compute_specs/mitmproxy/service/Capture__Ring_Buffer.py          # NEW
sg_compute_specs/mitmproxy/docker/images/agent_mitmproxy/...        # intercept script edits
```

`GET /capture/network-log/{run_id}` → NDJSON of flows tagged with that
`X-SG-Run-Id`. Ring buffer is in-memory (24h or N MB, whichever first).
Tests: real local HTTPServer fake (same pattern as `test_Routes__Web`).

### Slice 5 — End-to-end deploy test  (QA repo / integration tests)

Spin up a real `sp vault-app create --with-playwright --wait`; seed a
known QA vault; trigger one scenario via HTTP; assert: result JSON
appears in `runs/<...>/`, network log is non-empty, all assertions
`PASSED`. `sp vault-app delete` regardless of outcome.

### Slice 6 — Schedule / watch modes  (QA repo, post-MVP)

Out of MVP scope. Runner exposes an HTTP trigger; cron / GitHub
Actions / event-driven scheduling is deployer choice. No substrate
change required.

---

## 7. What the QA app does NOT need from this repo

By design — preserved from v1, still true:

- **No `Schema__QA__*`** in `sg_compute_specs/playwright/`.
- **No `Routes__QA`** on the playwright FastAPI.
- **No `Assertion__Evaluator`** in `sg_compute_specs/`.
- **No QA scheduler spec.**
- **No daily-summary / report generators in the substrate.**

The only thing this pack asks of the substrate repo is slice 4.

---

## 8. Open questions (refreshed from v1)

| # | Question | Recommended answer |
|---|---|---|
| Q1 | Where does the QA vault-app's code live? | **New repo** `SGraph-AI__Service__QA-Util` (or similar). Don't put it under `sg_compute_specs/qa/` — keeps the substrate generic and the QA app independently versioned. (Architect lean unchanged from v1.) |
| Q2 | `IFRAME_INJECTION` execution mode in scope? | **No.** Closed via v2 delta. Substrate has only real-browser; iframe-mode is a *client* concern. |
| Q3 | Per-run network log — pull or push? | **Pull** via `GET /capture/network-log/{run_id}`. Simpler; matches `Routes__Web`; no bus dependency. |
| Q4 | Run-id format? | `YYYY-MM-DDTHH-mm-ssZ__{scenario_id}__{uuid8}`. Sortable + greppable in the vault tree. Enforced by the QA runner; `Safe_Str__Id` validates the shape. |
| Q5 | Idempotency on re-runs of the same run-id? | Runner refuses to overwrite an existing `runs/<...>/result.json`. Re-runs require a fresh uuid8. |
| Q6 | Free-form assertions vs typed registry? | **Typed only.** Unknown types rejected at parse. Adds to the registry, not escape hatches. |
| Q7 | Add `qa-runner` to the substrate's vault-app compose? | **No** — keeps the substrate generic. The QA app's deploy story adds the container on top. |
| Q8 | What schedules the runner? | MVP: manual HTTP trigger. Post-MVP: cron in the container, GitHub Actions, or event-driven — operator choice. |
| Q9 (new in v0.2.19) | How does the QA runner reach the vault on TLS-on stacks (cert hostname mismatch)? | Internal call to `https://sg-send-vault` with `verify=False` — same single-host docker network, the access token is the actual gate. Cert verification adds nothing here. |

---

## 9. References

- `00__README.md` — this pack's index + the status table.
- `01__substrate-contract.md` — the substrate's API contract the QA app builds against.
- `library/guides/v0.2.6__playwright-api-for-agents.md` — Playwright REST API guide. Hand this to any agent (including the QA runner's own AI-driven scenarios) that needs to drive `/sequence/execute`.
- `team/comms/briefs/v0.2.6__vault-to-playwright-api.md` — internal vs external URLs + auth shape.
- `team/comms/briefs/v0.2.6__qa-vault-app/` — v1 of this pack; **superseded**, kept for historical context.

Source briefs (superseded):

- `team/humans/dinis_cruz/claude-code-web/05/13/21/v0.2.6__arch-plan__qa-service.md`
- `team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md`

---

*Next: open the QA app's repo (Q1), start slice 1 (schemas, no behaviour, parallelisable). Slice 4 (per-run mitmproxy capture) is independent and can start in parallel by a different contributor.*
