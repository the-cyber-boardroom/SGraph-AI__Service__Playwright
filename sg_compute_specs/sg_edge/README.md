# sg_edge — SG/Edge central edge tier

Scale-to-zero edge in front of vault targets: **CloudFront + wildcard ACM →
OpenResty proxy fleet → vault backends**, coordinated by an **Edge Waker** with
**DNS-as-registry** state and **no coordination service** (convergent
reconciliation, no lock). This package is the SG/Edge spec — a purely additive
sibling to `vault_app` / `vault_publish`.

> Status: **Phase 1 control plane + assets + bench core landed and tested.**
> Live-AWS wiring (EC2 launcher/terminator, `Setup__*`) and the `sg edge` CLI are
> not built yet. See the plans below.

## What exists today

| Area | Class | What it does |
|---|---|---|
| Wire format | `service/SG_Edge__TXT__Builder` | compose/parse `_sg.<slug>` routing TXT (`v=1;ip=…;port=…;type=…;launched=…`) |
| Wire format | `service/SG_Edge__State__Builder` | compose/parse `_state.<parent>` teardown TXT (`zero_streak=N;updated=N`) |
| DNS registry | `service/SG_Edge__DNS__Helper` | over `sg aws dns`: `proxies.<parent>` A membership, `_state` TXT counter, `_sg.*` active-slug read |
| Control loop | `service/SG_Edge__Fleet__Reconciler` | convergent `ensure_booting` / `reconcile` (scale-up) / `idle_check` (teardown); EC2 seams injected |
| Edge Waker | `lambdas/edge_waker/Fast_API__Edge_Waker` + `routes/Routes__Edge_Waker` | `Serverless__Fast_API` Lambda: `/__edge__/health\|status\|reconcile\|idle-check` + cold-cold loading page |
| Proxy rig | `proxy/nginx.conf` + `service/SG_Edge__Proxy__User_Data` | OpenResty: `:80` public static short-circuit + `:8089` VPC-private `/_edge/*` mgmt surface; EC2 cloud-init |
| CloudFront fn | `cloudfront_function/viewer_request.js` + `service/SG_Edge__CloudFront__Function` | viewer-request: preserve Host, extract slug → `X-SG-Host` / `X-SG-Slug` |
| Bench core | `bench/Edge_Bench__Runner` + `Edge_Bench__Stats` | p50/p95/p99 percentiles → PASS/WARN/FAIL verdicts vs doc-05 target/hard_fail thresholds |

State model (all in DNS, nothing else): `proxies.<parent>` A (fleet membership),
`_state.<parent>` TXT (zero_streak teardown counter), `_sg.<slug>.<parent>` TXT
(routing, read-only here — written by the Vault Waker in Phase 2).

## Not built yet (deferred — see plans)

- **EC2 launcher/terminator** wiring the reconciler's `_launcher`/`_terminator`
  seams; **`Setup__*`** provisioning (ACM/IAM/Lambda/CF/DNS) — live-AWS, Slice 5.
- **`sg edge` CLI** — no CLI surface exists yet; SG/Edge is reachable only via
  pytest and the Edge Waker FastAPI routes. Plan: `../../team/comms/plans/v0.2.37__sg-edge/sg-edge-cli-plan.md`.
- **`sg edge bench` scenarios** (P-*/F-*/X-*) + docker-compose local stack — Slice 6.

## Running the tests

```bash
python3   -m pytest sg_compute_specs/sg_edge/tests/   # 3.11: 77 pass, 6 skip (FastAPI)
python3.12 -m pytest sg_compute_specs/sg_edge/tests/  # 3.12: 83 pass (FastAPI included)
```

The 6 `test_Fast_API__Edge_Waker` tests need `osbot-fast-api-serverless` (Python
≥3.12) + `httpx`; they `@skipUnless` cleanly on 3.11. Everything else runs on
3.11. No mocks, no patches — AWS-touching tests use `Route53__AWS__Client__In_Memory`.

## Plans & history

- Implementation plan: `../../team/comms/plans/v0.2.37__sg-edge/README.md`
- CLI plan: `../../team/comms/plans/v0.2.37__sg-edge/sg-edge-cli-plan.md`
- Briefs: `../../team/humans/dinis_cruz/briefs/05/20/sg-edge/`
- Debriefs: `../../team/claude/debriefs/` (search `sg-edge`)
