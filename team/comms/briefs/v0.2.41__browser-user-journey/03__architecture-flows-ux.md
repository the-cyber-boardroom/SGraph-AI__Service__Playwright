---
title: "Browser User-Journey — 03 — Architecture, flows & UX (ASCII)"
version: v0.2.41
date: 2026-05-26
audience: Architect / Dev / QA / DevOps — the picture, before the code
note: All diagrams are ASCII so they render in any monospace viewer and diff cleanly in git.
---

# 03 — Architecture, flows & UX

Companion to `02__platform-design.md`. Everything drawn here is specified in
00–02; this file is the picture.

Legend: `[ box ]` = container/process · `( store )` = data · `══▶` = control/RPC
· `──▶` = data/HTTP · `··▶` = on-demand (created at runtime) · `✓/✗` = pass/fail.

---

## 1. System architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  OPERATOR  (laptop / CI / web)                                                 │
│                                                                                │
│   sg browser user-journey …        Cockpit TUI            Chat cockpit TUI     │
│   (thin: start/stop/monitor)       (live worker grid)     (LLM talks to tools) │
│            │                              │                       │            │
│            │                              └───────────┬───────────┘            │
│            │ control-plane API                        │ conductor API          │
│            │ /api/specs/user-journey                  │ (public_ip + X-API-Key) │
│            │ (stack lifecycle)                         │ (suite lifecycle)       │
└────────────┼──────────────────────────────────────────┼────────────────────────┘
             │                                           │
             ▼                                           ▼
┌──────────────────────────── EPHEMERAL EC2 (vault-app --with-playwright + conductor) ──┐
│  docker network: vault-net                                                             │
│                                                                                        │
│  ┌────────────────┐   ┌──────────────────┐   ┌───────────────────┐  ┌──────────────┐  │
│  │ [ sg-send-vault]│   │ [ conductor ]    │   │ [ agent-mitmproxy]│  │ [ host-plane]│  │
│  │  :443 HTTPS     │   │  suite API       │   │  proxy   :8080    │  │  :19009      │  │
│  │  ( journeys/ )  │◀══│  /var/run/       │   │  mitmweb :8081    │  │  /pods /shell│  │
│  │  ( suites/   )  │   │   docker.sock ───┼─┐ │  admin   :8000    │  │  Docker sock │  │
│  │  ( runs/     )  │══▶│  Result          │ │ │  /capture/        │  │              │  │
│  │  ( runs/ ◀ write)│   │   Aggregator     │ │ │   network-log/    │  │              │  │
│  └────────────────┘   └──────────────────┘ │ │   {run_id}  (#4)   │  └──────────────┘  │
│         ▲                                   │ └───────▲───────────┘                     │
│         │ read journey / write result       │ docker  │ pull per-run flows               │
│         │                                    │ run ··▶ │                                  │
│         │              ┌─────────────────────┴────────┴───────────────────────────┐     │
│         │              │  WORKERS  (created on demand, N per suite entry)          │     │
│         │              │  [ runner 1 ] [ runner 2 ] [ runner 3 ] … [ runner N ]    │     │
│         └──────────────┤  image: diniscruz/sg-journey-runner (FROM playwright base)│     │
│                        │  runs Playwright CORE in-process → Step__Executor          │     │
│                        │  proxy=agent-mitmproxy:8080 · header X-SG-Run-Id=<run_id>  │     │
│                        └───────────────────────────────┬───────────────────────────┘     │
│   ( sg-playwright service — substrate, used only for ad-hoc single runs )         │       │
└───────────────────────────────────────────────────────┼───────────────────────────────────┘
                                                         │ HTTP(S) via mitmproxy
                                                         ▼
                                                 target site(s) under test
```

Responsibility, one line each:

```
conductor      owns SUITES; fans out workers (docker socket); aggregates; suite API
worker         owns ONE journey run; reuses Playwright core; writes result to vault
agent-mitmproxy owns capture + interceptors; per-run flows via X-SG-Run-Id (#4)
sg-send-vault  owns journeys/ + suites/ (input) and runs/ (output), sgit-versioned
host-plane     generic introspection (logs/stats/shell) — optional for the operator
CLI            thin remote: create/delete stack, start/stop suite, status
TUIs           the product: live cockpit + LLM chat cockpit (one tool-API provider)
```

---

## 2. Flow — provision a stack

```
operator         control-plane           AWS / EC2                stack (vault-net)
   │  create [--interceptor-script F]        │                          │
   │═════════════════════════════════════════▶│  launch EC2 + user-data  │
   │                                          │═════════════════════════▶│ vault-app
   │                                          │                          │  --with-playwright
   │                                          │                          │  + conductor (compose)
   │                                          │                          │  + interceptor → active.py
   │   wait (health)                          │   HTTPS probe :443/:80    │
   │═════════════════════════════════════════▶│═════════════════════════▶│  healthy ✓
   │◀── info: public_ip, AccessToken (EC2 tag) ─                          │
   ▼
 ready → drive via Cockpit / Chat / CLI suite verbs
```

---

## 3. Flow — a suite run (the core loop)

```
 operator/LLM     conductor                 worker_i (×N, waves of concurrency)     vault     mitmproxy
     │ start_suite     │                              │                               │           │
     │═══════════════▶ │  read suites/<id>.json ──────┼──────────────────────────────▶│           │
     │                 │  read journeys/<jid>.json ───┼──────────────────────────────▶│           │
     │                 │  docker run runner ·········▶│ (image, env, X-SG-Run-Id,     │           │
     │                 │   (count, in waves)          │  proxy=mitmproxy)             │           │
     │                 │                              │  build sequence + synthetic    │           │
     │                 │                              │  wait_for/get_content          │           │
     │                 │                              │  run browser (core, in-proc) ──┼──────────▶│ capture
     │                 │                              │  GET /capture/network-log/{id}─┼───────────▶│ flows
     │                 │                              │  evaluate assertions (✓/✗)     │           │
     │                 │                              │  write runs/.../result.json ──▶│           │
     │                 │◀── POST worker status ───────│  exit                          │           │
     │  get_suite      │  aggregate (counts, p50/p95, flow totals)                      │           │
     │═══════════════▶ │── Schema__Suite__Run__Status ─▶                                │           │
     │◀── live status ─│  write runs/.../suite-result.json ─────────────────────────▶ │           │
     ▼
  cockpit grid updates live; suite DONE when all workers terminal
```

---

## 4. Flow — "with and without custom interceptors"

```
   stack A: create  (no --interceptor-script)        stack B: create --interceptor-script block-ads.py
        │  default addons only                              │  active.py = block-ads.py
        ▼                                                    ▼
   suite start  same-journey ×N                        suite start  same-journey ×N
        │                                                    │
        ▼                                                    ▼
   runs/.../ + network-log.ndjson  (baseline flows)     runs/.../ + network-log.ndjson  (intercepted)
        │                                                    │
        └──────────────► compare in cockpit / sgit diff ◀────┘
            (ad domains present in A, blocked/absent in B; status/header deltas)
```

> v1: one stack per interceptor config (ephemeral; cheap). Hot-swap on a live
> stack needs mitmproxy `PUT /config/interceptor` (unbuilt) — out of scope.

---

## 5. Flow — load = worker count × concurrency

```
 Schema__Suite__Entry { journey_id: checkout, count: 500, concurrency: 50 }

 conductor schedules 500 runners in waves of 50:

   wave 1  [#001 … #050]  ▓▓▓▓▓▓▓▓▓▓ running ──▶ terminal ✓/✗  ──▶ aggregate
   wave 2  [#051 … #100]              ▓▓▓▓▓▓▓▓▓▓ running ──▶ terminal …
   …                                                  …
   wave10  [#451 … #500]                                       ▓▓▓▓▓▓▓▓▓▓

 aggregates:  passed 488  failed 9  error 3   p50 1.9s  p95 4.2s  p99 7.8s
              flows 41,230   blocked 0   throughput ~38 journeys/min

 scale knob (cost-gated): scale_suite count=2000 → dry-run preview:
     "would launch 1500 more runner containers (~$X/hr).  Confirm? [y/N]"
```

Heavier-than-one-box load fans out across multiple stacks (later slice); each box
runs its own conductor + workers and reports to an aggregating client.

---

## 6. Flow — chat cockpit "talk to the tools" (agentic loop)

The LLM never touches the conductor directly; every call is gated by the
execution center (dry-run → mutation gate → audit).

```
 operator types: "run the checkout journey 200 times and give me the p95"
        │
        ▼
 Chat__Engine.send_turn_agentic(workflow=load, tools, name_map, grants)
        │
        ▼  backend.converse(...)            (bedrock | ollama | openrouter — neutral)
   LLM ─┴─▶ tool_use: start_suite{journey:checkout, count:200, concurrency:25}
        │
        ▼  center.execute('user-journey','start_suite', input, grants)
        │     ├─ precondition ✓   param-schema ✓   grants(load) ✓   IAM ✓
        │     ├─ DRY-RUN preview: "200 runners, ~$Y"   ── mutation gate ──▶ confirm ✓
        │     ├─ provider.dispatch → Conductor__Client → POST /suites
        │     └─ AUDIT log (who/what/when/result)
        │
        ▼  tool_result ──▶ LLM           (loop ≤ max_steps=6)
   LLM ─┴─▶ tool_use: get_suite{suite_run_id} ──▶ center.execute (read, no gate)
        │
        ▼  tool_result {p95: 4.2s, passed:191, failed:9}
   LLM ─┴─▶ "Done. 200 runs: 191 ✓ / 9 ✗. p95 = 4.2s. 9 failures were 504s on /pay."
        ▼
 transcript shows answer + collapsed Chat__Tool_Calls cards (start_suite, get_suite)
```

---

## 7. UX — the Cockpit TUI (`sg browser user-journey tui <stack>`)

```
┌─ sg browser · user-journey · cockpit ───────────── stack: uj-quiet-fermi ──── ✓ healthy ─┐
│ suite: checkout-load-500   state: RUNNING   elapsed 02:14   [s]tart [x]stop [r]efresh [q] │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ WORKERS  (500 · 50 in-flight)                          AGGREGATES                        │
│  #001 ✓  #002 ✓  #003 ✓  #004 ✗  #005 ✓  #006 ⠿       passed   488   ▓▓▓▓▓▓▓▓▓▓▓▓▓░ 97%  │
│  #007 ⠿  #008 ✓  #009 ✓  #010 ⠿  #011 ✓  #012 ✓       failed     9                       │
│  #013 ✓  #014 ⠿  #015 ✗  #016 ✓  #017 ⠿  #018 ✓       error      3                       │
│  …                                          (scroll)   p50 1.9s · p95 4.2s · p99 7.8s     │
│  legend: ✓ pass  ✗ fail  ⠿ running  · pending          ~38 journeys/min                  │
├──────────────────────────────────── LIVE FLOWS (mitmproxy) ─────────────────────────────┤
│  14:02:41  GET  https://shop.test/cart            200   412ms   #007                     │
│  14:02:41  POST https://shop.test/pay             504  3211ms   #004  ✗ STATUS_CODE       │
│  14:02:42  GET  https://cdn.ads.test/px.gif       ───   blocked  #007  (interceptor)      │
│  14:02:42  GET  https://shop.test/confirm         200   388ms   #007                     │
├──────────────────────────────────── DRILL-DOWN (#004) ──────────────────────────────────┤
│  journey checkout · FAILED · 3.4s   assertions: URL_CONTAINS ✓  STATUS_CODE_EQUALS ✗      │
│  runs/2026/05/26/checkout-load-500__…/workers/checkout__00004__c3d4/                      │
│  [enter] open result.json   [l] worker logs   [n] network-log.ndjson   [p] screenshots    │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. UX — the Chat cockpit (`sg browser user-journey chat <stack> --workflow load`)

```
┌─ user-journey · chat ───── stack: uj-quiet-fermi ── workflow: load ── model: claude ──────┐
│                                                                              cost $0.014  │
│  you ▸ run the checkout journey 200 times and give me the p95                             │
│                                                                                           │
│  ⚙ tool · start_suite { journey: checkout, count: 200, concurrency: 25 }      [expand ▸]  │
│      dry-run: would launch 200 runners (~$Y/hr)  →  confirmed                              │
│  ⚙ tool · get_suite { suite_run_id: …a1b2 }                                   [expand ▸]  │
│                                                                                           │
│  claude ▸ Done. 200 runs: 191 ✓ / 9 ✗ (3 errored).                                        │
│          p50 1.9s · p95 4.2s · p99 7.8s. The 9 failures were 504s on POST /pay —          │
│          STATUS_CODE_EQUALS(200) failed. Want me to re-run just the failures?             │
│                                                                                           │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ ▸ message…                                                  [f2] inspect  [f3] runs  ↵send│
└───────────────────────────────────────────────────────────────────────────────────────┘
   workflow=monitor would hide start/scale/stop; the model only sees granted tools.
```

---

## 9. UX — the CLI (thin: start / stop / monitor)

```
$ sg browser user-journey create --interceptor-script ./block-ads.py --wait
  ✓ uj-quiet-fermi  ip=… token=…(tag AccessToken)  conductor=https://…:PORT   [01:58]

$ sg browser user-journey suite start uj-quiet-fermi --file suites/checkout-load-500.json
  ▶ suite checkout-load-500  run …a1b2  (500 workers, 50 concurrent)   → watch: `… tui`

$ sg browser user-journey status uj-quiet-fermi --json | jq '.aggregates'
  { "passed": 488, "failed": 9, "error": 3, "p50_ms": 1900, "p95_ms": 4200, "p99_ms": 7800 }

$ sg browser user-journey delete uj-quiet-fermi
  ✓ terminated + SG cleaned
```

CI shape: `create` → `suite start --file nightly-regression.json` → poll
`status --json` → gate on `failed==0` → `delete` (always).

---

## 10. How this maps to existing code (so it stays "reuse, not rebuild")

```
 NEW (this platform)                        REUSED (already shipped)
 ───────────────────                        ────────────────────────
 conductor image + Suite__Runner            host-plane Docker-socket pattern (01 §A5)
 sg-journey-runner image                    Playwright core / Step__Executor (01 §A3)
 Schema__Journey__* / Schema__Suite__*      qa-vault-app schema design (v0.2.19/02)
 Journey__Assertion__Evaluator              qa pattern: stateless, synthetic steps
 GET /capture/network-log/{run_id}          qa "slice 4" (designed; we build it)
 User_Journey__Tui_Api__Provider            Tui_Api__Execution_Center + workflows (01 §B)
 Cockpit + chat screens                     Bedrock__Chat__Screen widgets + send_turn_agentic
 sg browser group + user-journey spec       Spec__CLI__Builder + nav_group BROWSERS
                                            vault-app --with-playwright substrate (01 §A1)
```

---

*This is the picture for 00–02. Start slice 1 (per-run capture) and slice 2
(schemas) in parallel; they unblock everything downstream.*
