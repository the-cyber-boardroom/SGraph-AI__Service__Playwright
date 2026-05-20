---
title: SG/Edge — MVP test and acceptance criteria
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer building the test harness; reviewer validating MVP readiness
scope: the CLI tool, test scenarios, acceptance thresholds, and measurement methodology that prove SG/Edge works
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__02-edge-fleet.md
  - sg-edge__03-targets.md
  - sg-edge__04-commercial-angles.md
companion_repo_patterns:
  - utils/ec2_boot_bench  # single-purpose benchmark utility
  - sgraph_ai_service_playwright__cli  # CLI structure
  - tests/{unit,integration,docker,deploy}  # multi-layer test pattern
  - team/comms/plans/vX.Y.Z__<topic>/README.md  # per-work-item plans
---

# Why this document exists

The other four docs describe what SG/Edge is and why it matters. This document describes **how we know it works** — the explicit scenarios, the measurements we collect, the acceptance thresholds we have to hit, and the CLI tool that lets us run all of this step-by-step or end-to-end.

The framing is deliberately conservative. The architecture has plausibly-correct properties; this document's job is to convert *plausibly* into *demonstrably*. Every scenario below answers a question that, until measured, we are guessing about.

This doc follows the patterns established in the companion repo:
- A single-purpose benchmark utility lives under `utils/`, similar to `ec2_boot_bench`
- The CLI is invocable as `sg edge_bench <scenario>` for individual scenarios or `sg edge_bench full` for end-to-end
- Acceptance criteria are explicit, machine-checkable, and reported as structured JSON
- Multi-layer test pattern: `unit / integration / docker / deploy` tests in `sg_compute__tests/`
- Per-work-item plans go in `team/comms/plans/v0.X.Y__sg-edge-mvp/README.md`

# The tool — `sg edge_bench`

A new CLI subsurface alongside `sg va` and `sg vp`, focused on validation rather than provisioning. The tool runs the same primitives that production code uses, but measures everything and reports structured results.

```
+---------------------------------------------------------------+
|                  sg edge_bench architecture                   |
+---------------------------------------------------------------+
|                                                               |
|   CLI entry                                                   |
|     sg edge_bench <scenario> [--repeat N] [--output FILE]     |
|                                                               |
|   |                                                           |
|   v                                                           |
|                                                               |
|   Scenario runner (Type_Safe class)                           |
|     - resolves scenario name to method                        |
|     - sets up clean state (or fails fast)                     |
|     - runs scenario N times                                   |
|     - collects timing for each step                           |
|     - tears down                                              |
|     - emits structured JSON                                   |
|                                                               |
|   |                                                           |
|   v                                                           |
|                                                               |
|   Per-scenario implementation                                 |
|     - uses sg_compute_specs primitives (NOT a separate stack) |
|     - records timestamps at well-defined events               |
|     - asserts acceptance criteria; raises on failure          |
|                                                               |
|   |                                                           |
|   v                                                           |
|                                                               |
|   Output                                                      |
|     - stdout: human-readable summary                          |
|     - file: structured JSON with all measurements             |
|     - exit code: 0 = passed all criteria, non-zero = failed   |
|                                                               |
+---------------------------------------------------------------+
```

The tool is intentionally single-purpose. It doesn't replace `pytest` for unit tests, doesn't replace production monitoring for ongoing observability. It's the harness for proving each architectural claim under controlled conditions, and for catching regressions.

# Scenario catalog

Scenarios are organised in three tiers — primitives (one thing in isolation), flows (multiple primitives composed), failure injection (what happens when things break). Each scenario is independently runnable.

## Tier 1 — primitive measurements

These validate individual building blocks before composing them. If any of these is unreliable, downstream flows can't be trusted.

```
+----------------------------------------------------------------------+
|  ID         |  Scenario name              |  What it measures        |
+----------------------------------------------------------------------+
|  P-01       |  ec2_boot_time              |  RunInstances API call   |
|             |                             |  to TCP-accepting        |
|             |                             |                          |
|  P-02       |  fargate_task_boot          |  RunTask API call to     |
|             |                             |  TCP-accepting           |
|             |                             |                          |
|  P-03       |  route53_record_write       |  ChangeResourceRecordSets|
|             |                             |  call to record visible  |
|             |                             |  in dig from external    |
|             |                             |                          |
|  P-04       |  route53_txt_propagation    |  TXT record write to     |
|             |                             |  resolvable from all     |
|             |                             |  CF POPs                 |
|             |                             |                          |
|  P-05       |  cf_origin_dns_refresh      |  Time for CF to see a    |
|             |                             |  changed A record on its |
|             |                             |  origin domain           |
|             |                             |                          |
|  P-06       |  cf_origin_failover         |  Time from primary       |
|             |                             |  unreachable to secondary|
|             |                             |  serving the request     |
|             |                             |                          |
|  P-07       |  openresty_static_response  |  Cold-process to first   |
|             |                             |  successful response on  |
|             |                             |  static site (no sidecar)|
|             |                             |                          |
|  P-08       |  openresty_dynamic_lookup   |  Per-request latency for |
|             |                             |  A + TXT lookup + proxy  |
|             |                             |  (warm cache)            |
|             |                             |                          |
|  P-09       |  openresty_cold_lookup      |  Per-request latency for |
|             |                             |  A + TXT lookup + proxy  |
|             |                             |  (cache miss, DNS hit)   |
|             |                             |                          |
|  P-10       |  lambda_function_url_cold   |  Cold start of Edge      |
|             |                             |  Waker Function URL      |
|             |                             |                          |
|  P-11       |  ec2_terminate_time         |  TerminateInstances API  |
|             |                             |  to instance gone        |
|             |                             |                          |
|  P-12       |  slug_not_found_serve_time  |  Time for "slug not      |
|             |                             |  recognised" page when   |
|             |                             |  A record is NXDOMAIN    |
+----------------------------------------------------------------------+
```

Each primitive scenario produces a histogram (we run it >=10x). The *variance* matters as much as the median — high-variance steps (like ALB provisioning, which is why we don't use ALB) inform architecture choices.

## Tier 2 — composed flows

These exercise multiple primitives in the sequences the real architecture uses. They're the "does it actually work end-to-end" tests.

```
+----------------------------------------------------------------------+
|  ID    |  Flow name                  |  Composed from                |
+----------------------------------------------------------------------+
|  F-01  |  edge_cold_cold_boot        |  P-10 (Lambda cold)           |
|        |  (Edge Waker triggered,     |  + P-01 (EC2 boot)            |
|        |   fleet from zero, no       |  + P-03 (A record write)      |
|        |   vault target involved)    |  + P-05 (CF DNS refresh)      |
|        |                             |  + P-07 (OpenResty ready)     |
|        |                             |                               |
|  F-02  |  edge_warm_request          |  P-08 only                    |
|        |  (typical hit-warm-fleet    |                               |
|        |   path)                     |                               |
|        |                             |                               |
|  F-03  |  vault_cold_boot            |  P-02 or P-01                 |
|        |  (existing flow - control)  |  + P-03 + P-04                |
|        |                             |                               |
|  F-04  |  edge_plus_vault_parallel   |  F-01 || F-03                 |
|        |  (the key optimization -    |  in parallel                  |
|        |   parallel edge and target  |  reported as max() not sum()  |
|        |   boot)                     |                               |
|        |                             |                               |
|  F-05  |  edge_plus_vault_serial     |  F-01 then F-03               |
|        |  (control - what we'd see   |  for comparison with F-04     |
|        |   without parallelization)  |                               |
|        |                             |                               |
|  F-06  |  cold_to_warm_to_cold       |  F-01 + steady traffic        |
|        |  (full cycle: cold-cold ->  |  + idle teardown              |
|        |   warm -> idle -> teardown) |  measured end-to-end          |
|        |                             |                               |
|  F-07  |  many_slugs_one_proxy       |  N vaults provisioned,        |
|        |  (capacity per proxy)       |  all traffic through 1 proxy, |
|        |                             |  measure latency under load   |
|        |                             |                               |
|  F-08  |  registered_but_dormant     |  Slug has A record but no     |
|        |  (the new "dormant" state   |  TXT; first request triggers  |
|        |   from doc 03)              |  Vault Waker without need to  |
|        |                             |  boot proxy fleet (warm path) |
+----------------------------------------------------------------------+
```

F-04 vs F-05 specifically validates the parallel-boot optimization. If F-04 isn't materially faster than F-05, the optimization isn't real and we should drop it from the design.

F-08 validates the registered/dormant case — the slug has an A record but its TXT is missing (e.g. has never been opened, or instance was terminated). This is a common Phase 2 path because every new customer starts here.

## Tier 3 — failure injection

These validate that the architecture degrades gracefully. Most cause real harm if they happen unexpectedly; the test is whether the system recovers without operator intervention.

```
+----------------------------------------------------------------------+
|  ID    |  Failure scenario             |  Expected behavior          |
+----------------------------------------------------------------------+
|  X-01  |  proxy_killed_during_request  |  CF retries, in-flight req  |
|        |                               |  fails once but next req    |
|        |                               |  succeeds (DNS health check |
|        |                               |  removes dead IP)           |
|        |                               |                             |
|  X-02  |  vault_killed_after_provision |  Proxy returns 502, fires   |
|        |                               |  Vault Waker async, user    |
|        |                               |  sees loading page          |
|        |                               |                             |
|  X-03  |  vault_ip_changed_mid_run     |  Proxy invalidates cache,   |
|        |  (EC2 stop/start changes IP)  |  re-reads TXT, succeeds     |
|        |                               |                             |
|  X-04  |  edge_waker_killed_mid_boot   |  Idempotent: next CF        |
|        |                               |  failover finishes the      |
|        |                               |  partially-booted state     |
|        |                               |  via reconciliation         |
|        |                               |                             |
|  X-05  |  concurrent_cold_cold_5x      |  5 simultaneous CF failover |
|        |  (no S3 lock, but bounded     |  triggers: at most 2-3      |
|        |   over-provisioning)          |  proxies launched, no       |
|        |                               |  errors visible to users    |
|        |                               |                             |
|  X-06  |  txt_record_missing           |  Proxy triggers Vault Waker |
|        |  (slug registered but dormant)|  and serves loading page    |
|        |                               |  (NOT a 404)                |
|        |                               |                             |
|  X-07  |  a_record_missing             |  Proxy serves "slug not     |
|        |  (unknown slug)               |  recognised" 404; rate-     |
|        |                               |  limited                    |
|        |                               |                             |
|  X-08  |  txt_record_malformed         |  Proxy returns 502, logs    |
|        |                               |  the bad record, no crashes |
|        |                               |                             |
|  X-09  |  vault_security_group_blocks  |  Proxy returns 502 quickly  |
|        |  proxy traffic                |  (SG rejection is fast),    |
|        |                               |  not a slow timeout         |
|        |                               |                             |
|  X-10  |  cf_origin_health_unreachable |  CF correctly fails over to |
|        |                               |  secondary even with edge   |
|        |                               |  cache layers in the way    |
|        |                               |                             |
|  X-11  |  reaper_orphan_cleanup        |  Vault Reaper detects       |
|        |                               |  abandoned TXT entries and  |
|        |                               |  removes them; A records    |
|        |                               |  untouched; no live vault   |
|        |                               |  wrongly reaped             |
|        |                               |                             |
|  X-12  |  enumeration_attempt          |  100 random subdomains      |
|        |  (security)                   |  hammered: rate limit       |
|        |                               |  kicks in, no proxy DoS     |
+----------------------------------------------------------------------+
```

X-05 deserves special attention because it validates the no-S3-lock decision. The architecture relies on convergent reconciliation rather than locking; this test confirms that under concurrent cold-cold triggers we don't get pathological over-provisioning (e.g. 5+ proxies for one slug) and no user-visible errors.

X-11 validates the Reaper's TXT-only scope. The test must include a case where a live vault has a healthy heartbeat — the Reaper must NOT remove it. The test must also include a case where a vault is dead — Reaper removes TXT but A record stays untouched.

# Acceptance criteria

These are the explicit thresholds. The build is acceptable when every criterion below passes 10 consecutive runs across two AWS regions.

```
+----------------------------------------------------------------------+
|  Scenario   |  Metric           |  Target             |  Hard fail   |
+----------------------------------------------------------------------+
|  P-01       |  p50 boot         |  <60s               |  >120s       |
|  P-01       |  p95 boot         |  <90s               |  >180s       |
|  P-02       |  p50 boot         |  <30s               |  >60s        |
|  P-02       |  p95 boot         |  <45s               |  >90s        |
|  P-03       |  p50 latency      |  <2s                |  >10s        |
|  P-04       |  p95 propagation  |  <30s               |  >120s       |
|  P-05       |  p95 refresh      |  <60s               |  >180s       |
|  P-06       |  p50 failover     |  <2s                |  >5s         |
|  P-06       |  p95 failover     |  <5s                |  >15s        |
|  P-07       |  p50 ready        |  <20s               |  >45s        |
|             |  (note: no        |                                    |
|             |  sidecars in MVP) |                                    |
|  P-08       |  p99 latency      |  <10ms              |  >50ms       |
|  P-09       |  p99 latency      |  <50ms              |  >200ms      |
|             |  (two DNS lookups |                                    |
|             |   on cold path)   |                                    |
|  P-10       |  p95 cold start   |  <1s                |  >3s         |
|  P-12       |  p99 latency      |  <20ms              |  >100ms      |
|                                                                      |
|  F-01       |  p95 end-to-end   |  <90s               |  >180s       |
|  F-02       |  p99 end-to-end   |  <50ms in-region    |  >200ms      |
|  F-04       |  p95 end-to-end   |  <90s               |  >180s       |
|  F-04 vs    |  reduction vs     |  >=30% faster than  |  no gain     |
|    F-05     |  serial baseline  |  serial             |              |
|  F-07       |  p99 latency      |  <30ms with 100     |  >100ms      |
|             |  under load       |  concurrent slugs   |              |
|  F-08       |  p95 end-to-end   |  <90s (just vault   |  >180s       |
|             |  (dormant slug    |  boot, proxy        |              |
|             |  awakening)       |  already warm)      |              |
|                                                                      |
|  X-01       |  next req succeeds|  <60s after kill    |  >180s       |
|  X-02       |  loading page     |  immediate          |  any error   |
|             |  served                                  visible to    |
|             |                                          user          |
|  X-03       |  recovery time    |  <30s               |  >120s       |
|  X-04       |  next failover    |  succeeds w/o human |  human       |
|             |  recovery         |  intervention       |  needed      |
|  X-05       |  proxies launched |  <=3 (target 1 +    |  >5          |
|             |                   |   tolerable over-   |              |
|             |                   |   provision)        |              |
|  X-05       |  user-visible     |  none               |  >0          |
|             |  errors                                                |
|  X-06       |  loading page     |  served on first    |  any error   |
|             |  served, waker    |  request                          |
|             |  triggered                                             |
|  X-07       |  "slug not        |  rate-limited       |  uncapped    |
|             |  recognised" page |  (max ~5/sec/IP)    |              |
|  X-11       |  live vault NOT   |  always preserved   |  any false   |
|             |  reaped                                  reap          |
|  X-12       |  proxy CPU under  |  <50% with 100      |  >80%        |
|             |  enumeration      |  rps random         |              |
|             |  attack           |  subdomains         |              |
+----------------------------------------------------------------------+
```

Two clarifications on the methodology:

1. **"Hard fail" is the bar where MVP is not shipped.** Between "target" and "hard fail" we ship with a known-issues note. The architecture is good-enough at target; below hard-fail it's not credible.

2. **Two regions is the minimum.** Many AWS-specific behaviors (Route 53 propagation, CF POP cache, EC2 boot variance) differ regionally. The MVP must demonstrate the criteria in at least two regions to be considered validated.

# Phase 1 — what we test first

From `sg-edge__01-solution-overview.md`, Phase 1 is "prove the edge tier in isolation, with static-site short-circuit instead of real routing." The scenarios that map to Phase 1:

```
+----------------------------------------------------------------------+
|  Phase 1 in-scope scenarios     |  Why first                         |
+----------------------------------------------------------------------+
|  P-01, P-03                     |  Validate EC2 + DNS primitives     |
|  P-05, P-06, P-07               |  Validate CF + OpenResty mechanics |
|  P-10                           |  Validate Edge Waker cold start    |
|  P-11                           |  Validate teardown                 |
|                                                                      |
|  F-01                           |  The big one - cold-cold boot of   |
|                                 |  the entire edge tier              |
|  F-06                           |  Cycle test - boot, idle, teardown,|
|                                 |  next boot                         |
|                                                                      |
|  X-04, X-05                     |  Edge Waker resilience under race  |
|                                 |  and failure (no S3 lock)          |
|  X-10                           |  CF origin failover correctness    |
|  X-12                           |  Static-site enumeration safety    |
+----------------------------------------------------------------------+

Deferred until Phase 2 (need real targets):
  P-02, P-04, P-08, P-09, P-12 (slug routing)
  F-02, F-03, F-04, F-05, F-07, F-08
  X-01, X-02, X-03, X-06, X-07, X-08, X-09, X-11
```

This subset is exactly what proves "the edge tier as a thing" works, with no dependency on changes to the Vault Waker or the vault target codebase. If any scenario in Phase 1 hard-fails, we redesign before going to Phase 2.

**Local vs AWS execution.** All Phase 1 scenarios run locally (using the docker-compose stack from the "Test environment topology" section) with the exception of the genuinely-AWS-specific timing tests: P-05 (CF DNS-cache refresh) and P-06 (CF origin failover end-to-end). Everything else — the Edge Waker reconciliation, the Lua hot path, the static-site response, the EC2-equivalent boot mechanics (mocked locally to a fast container start), the rate limiter, the OpenResty internals — runs against the local stack in seconds. The bench env exists only for the AWS-specific timing checks; everything else can be developed and regression-tested locally for tight iteration.

# What gets measured and how

For every scenario, the tool records a structured trace. Each trace is a list of named events with timestamps; the tool computes durations between named events as the scenario's measurements.

```
+----------------------------------------------------------------------+
|  Example trace from F-01 (edge_cold_cold_boot)                       |
+----------------------------------------------------------------------+
|  {                                                                   |
|    "scenario": "F-01__edge_cold_cold_boot",                          |
|    "run_id": "20260520T112233-abcd",                                 |
|    "region": "eu-west-1",                                            |
|    "events": [                                                       |
|      {"name": "cf_request_sent",         "ts": 0.000},               |
|      {"name": "cf_failover_to_secondary","ts": 1.234},               |
|      {"name": "lambda_invoked",          "ts": 1.456},               |
|      {"name": "ec2_run_instances_called","ts": 2.110},               |
|      {"name": "ec2_instance_pending",    "ts": 2.890},               |
|      {"name": "ec2_instance_running",    "ts": 23.450},              |
|      {"name": "ec2_user_data_complete",  "ts": 28.120},              |
|      {"name": "openresty_health_green",  "ts": 31.560},              |
|      {"name": "route53_a_record_written","ts": 32.890},              |
|      {"name": "cf_origin_resolved_new",  "ts": 41.020},              |
|      {"name": "user_request_succeeds",   "ts": 41.150}               |
|    ],                                                                |
|    "durations": {                                                    |
|      "failover_latency":     1.234,                                  |
|      "lambda_cold_start":    0.222,                                  |
|      "ec2_boot_total":      30.560,                                  |
|      "dns_propagation":      8.130,                                  |
|      "total_end_to_end":    41.150                                   |
|    },                                                                |
|    "criteria": {                                                     |
|      "F-01__p95_end_to_end": {"target": 90, "actual": 41.150,        |
|                                "result": "pass"}                     |
|    }                                                                 |
|  }                                                                   |
+----------------------------------------------------------------------+
```

The structured output is essential — it lets us:

- Diff runs to spot regressions
- Spot anomalies (which step got slower? was it AWS or our code?)
- Track median + p95 + p99 over time as the system evolves
- Plug into CI for automated regression detection
- Hand a customer or auditor a real measurement, not a marketing claim

# Reporting + dashboards

Two outputs from every run:

1. **Per-run JSON** — written to `~/.sg/edge_bench/runs/<run_id>.json`. Local file storage is sufficient for MVP — no S3, no long-term retention policy. The harness keeps recent runs on disk for diffing and trend spotting; older runs can be archived or discarded at the operator's discretion.

2. **Human summary** — emitted to stdout, looks like:
   ```
   F-01__edge_cold_cold_boot (10 runs, eu-west-1)
     end_to_end:     p50=39.1s  p95=43.8s  p99=51.2s  [target: <90s] PASS
     ec2_boot:       p50=29.4s  p95=32.1s  p99=37.5s
     dns_prop:       p50=8.0s   p95=12.3s  p99=15.8s
     lambda_cold:    p50=0.18s  p95=0.31s  p99=0.42s

   F-04__edge_plus_vault_parallel vs F-05__edge_plus_vault_serial
     parallel speedup: 38%  [target: >=30%] PASS
   ```

The structured data eventually drives a real dashboard (Grafana or similar), but for MVP a static HTML report from the JSON files is enough.

# Test environment topology

Two test environments — one local (for the fast development loop), one in AWS (for the slow, AWS-quirk-aware loop). They share the same `sg edge_bench` CLI; the difference is the `--target` flag.

```
+----------------------------------------------------------------------+
|  Environment   |  Purpose                  |  Lifetime               |
+----------------------------------------------------------------------+
|  local         |  Fast dev loop, 90% of    |  ephemeral, brought up  |
|                |  scenarios; no AWS quirks |  with docker compose,   |
|                |  but no real AWS APIs     |  torn down on demand    |
|                |                                                      |
|  bench         |  AWS-specific behavior:   |  permanent, but         |
|                |  CF DNS-cache refresh,    |  resources scale to     |
|                |  Route 53 propagation,    |  zero between runs      |
|                |  EC2 boot variance        |                          |
|                |                                                      |
|  dev-edge      |  Engineer sandbox         |  user-controlled         |
|                |                                                      |
|  staging-edge  |  Pre-prod validation,     |  always-on minimal       |
|                |  manual benchmark runs    |  fleet                   |
|                |                                                      |
|  prod-edge     |  Customer-facing          |  always-on for warm tier;|
|                |                           |  scale-to-zero for       |
|                |                           |  hibernation tier        |
+----------------------------------------------------------------------+
```

## Local environment

The full Phase 1 + Phase 2 architecture can be brought up locally — every component has a local equivalent. The local stack is a single `docker compose` file that runs:

- OpenResty in a container (the real proxy image, same Lua, same config)
- The Edge Waker as a FastAPI service container (same code as the Lambda Function URL, just run as long-lived HTTP)
- The Vault Waker similarly as a FastAPI service container
- A vault target container (the existing local-vault pattern, plain HTTP)
- A small DNS mock service (HTTP API the proxy talks to, simulating Route 53 lookups for A/TXT records) — OR — CoreDNS in a container with a file-backed zone
- A thin nginx in front of the proxy simulating CloudFront's TLS termination and origin-group failover

What this covers: every scenario where the unknowns are in our own code — the Lua hot path, the Waker reconciliation logic, the Reaper's slug_seen union, the A/TXT lifecycle correctness, the API key auth between proxy and target, the loading page UX. Scenarios run in seconds rather than the 60-90s of real AWS boots. Engineers run this on their laptops; CI runs it on every PR.

What it doesn't cover: CF DNS-cache refresh latency at POPs, Route 53 global propagation, EC2 boot variance under load, Lambda Function URL cold start behavior, real AWS rate limiting. Those are the AWS-specific scenarios — they need the bench env.

The CLI flag `--target=local` vs `--target=aws-bench` swaps between them; scenario implementations are identical otherwise. This is critical for getting tight iteration: most bugs are caught in seconds on the local stack, and only the genuinely AWS-specific tests pay the cost of real AWS round-trips.

## AWS bench environment

Domain conventions:
- bench: `*.bench-edge.sg-labs.app`
- dev: `*.dev-edge.sg-labs.app`
- staging: `*.staging-edge.sg-labs.app`
- prod: `*.cv.sgraph.ai`, `*.demos.sg-labs.app`, etc.

Each environment is one CloudFront distribution + one wildcard cert + one Route 53 zone, exactly as documented in `sg-edge__01-solution-overview.md`. The benchmark scenarios run against `bench-edge` so prod is untouched.

Every resource launched by the benchmark is tagged `purpose=edge-bench` plus the `run_id` for traceability. AWS costs from bench runs are covered by credits; we tag for hygiene and to spot anything unexpected, not for billing reasons.

# CI integration

Following the deploy-via-pytest pattern from the companion repo:

```
+----------------------------------------------------------------------+
|  CI workflow stages                                                  |
+----------------------------------------------------------------------+
|                                                                      |
|  on: pull_request                                                    |
|                                                                      |
|  1. unit_tests                                                       |
|     - sg_compute__tests/unit/* (no AWS)                              |
|     - <1 minute, blocks merge                                        |
|                                                                      |
|  2. integration_tests                                                |
|     - sg_compute__tests/integration/* (in-memory AWS via moto)       |
|     - <3 minutes                                                     |
|                                                                      |
|  3. edge_bench__local                                                |
|     - sg edge_bench primitives --target=local --repeat 3             |
|     - sg edge_bench flows      --target=local --repeat 3             |
|     - docker compose up; runs against local stack                    |
|     - <3 minutes total, no AWS calls                                 |
|                                                                      |
|  4. edge_bench__aws_primitives                                       |
|     - sg edge_bench primitives --target=aws-bench --region eu-west-1 |
|     - only the AWS-specific subset (P-05, P-06)                      |
|     - records to bench env                                           |
|     - <5 minutes total                                               |
|                                                                      |
|  5. edge_bench__aws_flows                                            |
|     - sg edge_bench flows --target=aws-bench --region eu-west-1      |
|     - <10 minutes                                                    |
|                                                                      |
|  6. edge_bench__failure_injection                                    |
|     - sg edge_bench failures --target=aws-bench --region eu-west-1   |
|     - only on main branch (these are expensive and noisy)            |
|                                                                      |
|  on: schedule (nightly)                                              |
|                                                                      |
|  7. edge_bench__full_matrix                                          |
|     - All scenarios x [eu-west-1, us-east-1] x repeat 10             |
|     - results stored in run JSON files                               |
|                                                                      |
+----------------------------------------------------------------------+
```

PR cannot merge if stages 1-5 fail. Stage 6 is informational on PRs but blocking on main. Stage 7 catches drift over time — if a step gets 20% slower week-over-week without a known cause, we investigate.

# Scenario walk-through — example

To make this concrete, here's what F-01 (edge_cold_cold_boot) actually does step-by-step:

```
$ sg edge_bench F-01 --region eu-west-1 --repeat 10

[setup] Ensuring bench environment is at zero state...
        - terminating any existing bench proxies
        - removing proxies.bench-edge.sg-labs.app A records
        - waiting 30s for DNS to converge

[run 1/10]
  09:23:01.000  cf_request_sent           https://t1.bench-edge.sg-labs.app/
  09:23:02.234  cf_failover_to_secondary  (after 1.234s)
  09:23:02.456  lambda_invoked
  09:23:03.110  ec2_run_instances_called
  09:23:03.890  ec2_instance_pending
  09:23:24.450  ec2_instance_running       (20.5s boot wait)
  09:23:29.120  ec2_user_data_complete     (4.6s user-data)
  09:23:32.560  openresty_health_green     (3.4s app start, no sidecars)
  09:23:33.890  route53_a_record_written
  09:23:42.020  cf_origin_resolved_new     (8.1s DNS propagation)
  09:23:42.150  user_request_succeeds      (TOTAL: 41.15s)

  [teardown] Terminating bench proxy, removing DNS records...

[run 2/10]
  ...

[summary]
  F-01__edge_cold_cold_boot (10 runs, eu-west-1)
    total:        p50=39.1s   p95=43.8s   p99=51.2s   [target <90s]   PASS
    failover:     p50=1.18s   p95=1.45s                [target <5s]    PASS
    ec2_boot:     p50=29.4s   p95=32.1s                [no target]
    dns_prop:     p50=8.0s    p95=12.3s                [target <60s]   PASS

  Result: PASSED 4/4 criteria
  Run data: ~/.sg/edge_bench/runs/F-01__20260520T112233-abcd.json
```

The walk-through is verbose deliberately. Engineers run this iteratively while debugging; the trace shows them which step regressed when something breaks.

# What's NOT in the MVP test surface

A few things explicitly out-of-scope for the MVP harness, to be added in Phase 2 or 3:

- **WebSocket testing.** Vault doesn't use WS today; if/when it does, scenarios for WS upgrade and long-lived connections get added.
- **Multi-region failover.** Multi-AZ within one region is in scope; failover across regions is Phase 3.
- **Cross-cloud failover.** The Hetzner standby for BCP is Phase 3 work; testing it is part of that workstream.
- **Load testing at production scale.** F-07 tests up to 100 concurrent slugs, which is plenty for MVP. Production capacity testing (1000s of concurrent slugs) is a separate effort with different tooling.
- **Pen-test of the edge layer.** Security validation is a separate discipline; we'll commission an external pen-test once the architecture is stable in staging.
- **Chaos engineering.** Random failure injection at production runtime (vs the structured X-* scenarios) is a Phase 3 maturity activity.
- **Sidecar-related scenarios.** Vector log shipping, CloudWatch agent, Edge Heartbeat — none of these exist in MVP; their tests come with Phase 3.

# Decisions (formerly open questions)

1. **Test data isolation between concurrent runs.** Not a concern for MVP — single operator running the benchmarks (no concurrent runs from multiple engineers, no CI parallelism on the same bench env). `run_id`-namespaced slugs are still used for traceability and to avoid stepping on the previous run's records, but no special concurrency-aware design is needed.
2. **AWS cost tracking for the bench env.** Tag every benchmark-launched resource with `purpose=edge-bench` and the `run_id` for hygiene. AWS costs are covered by credits, so this is for visibility and cleanup, not billing.
3. **What happens when a scenario fails?** Fail fast. No retries — neither on hard-fail criteria nor on transient AWS errors. A failure is signal; covering it up with a retry hides information we want to see. If a scenario is flaky enough that re-running helps, that itself is a finding worth investigating.
4. **Reporter compatibility.** JSON output only. No JUnit XML, no TAP — if CI integration needs another format later we can convert from the JSON, but it's not worth the surface area for MVP.
5. **Long-lived storage of historical runs.** Not in MVP scope. Local file storage (`~/.sg/edge_bench/runs/`) is enough — recent runs are kept for diffing and trend spotting, older runs can be archived or discarded when convenient. No S3 bucket, no time-based retention rules.
