---
title: SG/Edge — implementation plan (Phase 1, codebase-grounded)
version: v0.2.37
date: 2026-05-20
status: plan / in-progress
role: Dev
audience: implementing engineer (or next Claude thread) picking up SG/Edge
related:
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__01-solution-overview.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__02-edge-fleet.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__03-targets.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__04-commercial-angles.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge/sg-edge__05-mvp-test-and-acceptance.md
  - team/humans/dinis_cruz/briefs/05/20/fast-api/   (Edge Waker = FastAPI Lambda)
prior:
  - sg_compute_specs/vault_publish/                 (the Vault Waker — proven analogue)
  - sg_compute_specs/vault_publish/lambdas/waker/   (v0.1.17 Serverless__Fast_API Lambda template)
  - sg_compute/_for_osbot_aws/                       (combined-zip dependency Builder/Loader)
---

# Why this plan exists

The five `sg-edge__*` briefs (05/20, in `briefs/05/20/sg-edge/`) describe a central
edge tier — CloudFront + ACM wildcard → OpenResty proxy fleet → vault targets,
coordinated by two Wakers, with **DNS-as-registry** and **no coordination
service**. The briefs were written by an agent without deep knowledge of this
codebase, so they describe components in the abstract.

This plan re-grounds the design on what already exists. The headline: **almost
every AWS primitive SG/Edge needs already ships as a `sg aws *` module, and the
Edge Waker is just another `Serverless__Fast_API` Lambda** like the v0.1.17
vault-publish waker. We build on the existing surface; we do not reinvent it.

> **Zero-impact rule (owner directive).** Everything in this plan is purely
> additive — a new `sg_compute_specs/sg_edge/` spec plus new Lambda/asset modules.
> It MUST NOT change the behaviour of any existing `sg *` command. Nothing in the
> current tree imports `sg_edge`; the `sg` CLI surface is unchanged. Verified at
> each commit (import-graph grep + CLI-registration grep).

# What changed in the 05/20 brief rewrite (read if returning)

The briefs were substantially rewritten on 2026-05-20 (commit `647de5a`). The
deltas that reshaped this plan:

1. **The S3 `If-None-Match` lock is GONE.** "There is no S3 lock." The Edge Waker
   is **convergent**: it reads DNS ground truth and reconciles toward a target
   proxy count. Two racing invocations cost one extra `t4g.small` for a few
   minutes — a rounding error. No coordination service at all.
2. **All Edge Waker state lives in DNS.** Three record types:
   `proxies.<parent>` A (fleet membership), `_state.<parent>` TXT (`zero_streak`
   teardown counter), `_sg.<slug>.<parent>` TXT (routing, observed read-only).
3. **Module path is `sg_compute_specs/sg_edge/`** — NOT `edge` (doc 01 decision #2;
   matches the `vault_app` / `vault_publish` sibling pattern).
4. **Phase 1 has no proxy cert and no sidecars.** Plain HTTP CF→proxy (`listen 80`).
   No Vector / CloudWatch agent / heartbeat. Logging via nginx access log to
   stdout with `$remote_addr` omitted.
5. **Proxy↔target auth = `Serverless_Fast_API` X-API-Key** (the v0.1.17 pattern),
   injected by the proxy, validated by the target's middleware. Works locally too.
6. **Liveness source-of-truth = the proxies' in-memory `slug_seen`**, exposed at
   `/_edge/slug_seen` and unioned by the Reaper. No vault-side heartbeat, no SSM.
7. **New doc 05** defines a `sg edge_bench` CLI + acceptance thresholds + a local
   docker-compose stack (90% of scenarios run locally in seconds).

# Component → existing capability map

| Brief component | What it needs | Already exists | New work |
|---|---|---|---|
| CloudFront + wildcard ACM | TLS terminator, wildcard cert | `sg aws cf` (`CloudFront__AWS__Client`, `CloudFront__Distribution__Builder`, `ensure_distribution`, `wait_deployed`), `sg aws acm` (`ACM__AWS__Client`) | edge distribution config (`*.<parent>` alias + origin group) |
| CF Function (Host preserve, slug extract) | CF Function CRUD | `CloudFront__Function__AWS__Client` (`create`, `publish`, `attach_function_to_distribution`) | viewer-request JS source (in `sg_edge/cloudfront_function/`) |
| CF origin-group failover (primary=proxies, secondary=Edge Waker) | failover origin config | **`CloudFront__Origin__Failover__Builder` already exists** | wire primary/secondary for the edge |
| Edge Waker Lambda + Function URL | FastAPI Lambda, public Fn URL | `Serverless__Fast_API` + `Fast_API__Routes` (osbot); in-repo template `vault_publish/lambdas/waker/`; combined-deps `sg_compute/_for_osbot_aws/`; `sg aws lambda` (`deploy_from_folder`, `ensure_function_url`) | Edge Waker app + routes + reconciliation |
| Proxy fleet launch | RunInstances, security groups | `sg aws ec2` (`create_instance`, `create_stack`, `create_security_group`, `authorize_security_group_ingress`, `describe_instance`) | OpenResty user-data + edge SG |
| `proxies.<parent>` A records | Route 53 A CRUD | `sg aws dns` (`create_record`, `delete_record`, `list_records`, `upsert_a_alias_record`, `resolve_zone_for_fqdn`) | edge-scoped helpers |
| `_state.<parent>` TXT (zero_streak) | Route 53 TXT upsert | same `sg aws dns` client (`Enum__Route53__Record_Type` covers TXT) | `SG_Edge__State__Builder` (compose/parse) ✅ Slice 1 |
| `_sg.<slug>` TXT (routing) | Route 53 TXT read | same `sg aws dns` client | `SG_Edge__TXT__Builder` (compose/parse v=1) ✅ Slice 1 |
| Edge Waker / proxy IAM roles | role + inline policy | `sg aws iam` (`create_role`, `put_inline_policy`, `IAM__Trust_Policy__Builder`) | the two scoped policy docs |
| Readiness polling | proxy "is it up yet?" | HTTP probe pattern (vault_publish; no SSM module exists) | poll `<private-ip>:8089/_edge/health` over HTTP |
| Log shipping | CloudWatch Logs | EC2 default log driver captures stdout | nginx `log_format` with client IP omitted (no sidecar in MVP) |

## One deliberate departure from the briefs

**No SSM.** There is no `sg aws ssm` module and the rewritten briefs no longer
need one — readiness is an HTTP probe of `/_edge/health`, liveness is the proxies'
`slug_seen`, and teardown state is the `_state.<parent>` TXT. The proxy IAM role
needs only `logs:PutLogEvents` + `ec2:DescribeInstances` (own instance). This
matches the briefs and keeps blast radius minimal.

(The earlier version of this plan made an S3 `If-None-Match` `put_object` addition
the headline new primitive. The brief rewrite removed the lock, so that work is
**dropped** — no change to `S3__AWS__Client` is needed.)

# Decisions (from the rewritten brief "Decisions (formerly open questions)")

1. **No cert on the proxy** — plain HTTP CF→proxy (`listen 80`) in Phase 1.
2. **DNS cache TTLs are asymmetric** — A found 300s / A NXDOMAIN 60s; TXT found
   30s / TXT NXDOMAIN 5s (short so a freshly-written TXT is seen fast); health 10s.
3. **CF Function lives in `sg_compute_specs/sg_edge/cloudfront_function/`.**
4. **Proxy count is static for MVP** (`EDGE_PROXY_TARGET_COUNT`, e.g. 2). Auto-scale
   deferred to Phase 3 (needs bench load data).
5. **Log redaction** is in the nginx `log_format` (omit `$remote_addr`); the Vector
   sidecar is Phase 3.
6. **Proxy↔target auth** uses the existing `Serverless_Fast_API` X-API-Key.

# Package layout

New spec sibling to `vault_publish`, modelled on it:

```
sg_compute_specs/sg_edge/
  primitives/    Safe_Str__SG_Edge__Parent_Domain, Safe_Int__SG_Edge__Unix_Ts,
                 Safe_Int__SG_Edge__TXT_Version, Safe_Int__SG_Edge__Cycle_Count
  enums/         Enum__SG_Edge__Backend__Type, Enum__SG_Edge__Fleet__State
  schemas/       Schema__SG_Edge__TXT__Record   (the _sg.<slug> routing record)
                 Schema__SG_Edge__State__Record (the _state.<parent> teardown counter)
  service/       SG_Edge__TXT__Builder          (Slice 1, done — routing TXT)
                 SG_Edge__State__Builder        (Slice 1, done — _state TXT)
                 SG_Edge__DNS__Helper           (Slice 2 — over sg aws dns seam)
                 SG_Edge__Fleet__Reconciler     (Slice 3 — convergent loop)
  cloudfront_function/  viewer-request JS        (Slice 4)
  user_data/     OpenResty static-rig boot script (Slice 4)
  lambdas/edge_waker/   Serverless__Fast_API app + Fast_API__Routes + lambda_entry
                        + edge_waker__config (Slice 3/5; combined-deps loader)
  setup/         Setup__IAM / Setup__CF / Setup__Lambda / Setup__DNS  (Slice 5)
  tests/         co-located, no mocks
```

AWS-touching service classes take an injected client seam (the `vault_publish`
`_ec2_factory` pattern) so unit tests run against in-memory fakes — no mocks.

# Phase 1 slice sequence

Phase 1 = prove the edge tier in isolation behind a static-site short-circuit (no
vault target in the loop). 90% runs locally via the doc-05 docker-compose stack.

| Slice | Scope | AWS? | Status |
|---|---|---|---|
| **1 — typed foundation** | primitives, enums, `Schema__SG_Edge__TXT__Record` + `Schema__SG_Edge__State__Record`, `SG_Edge__TXT__Builder` + `SG_Edge__State__Builder`; 32 unit tests | none | **done** |
| 2 — DNS helper | `SG_Edge__DNS__Helper` over `sg aws dns`: write/read/delete `proxies.<parent>` A, upsert/read `_state.<parent>` TXT, read `_sg.<slug>` TXT; in-memory-fake tests | DNS (seam) | next |
| 3 — Edge Waker (FastAPI Lambda) | `lambdas/edge_waker/` — `Serverless__Fast_API` app + `Fast_API__Routes` + combined-deps loader; convergent reconciliation; parallel-fork to Vault Waker; HTTP readiness probe; loading page | Lambda/EC2 (seam) | |
| 4 — proxy rig + CF Function | OpenResty static-diagnostic user-data (`:80` public static short-circuit + `:8089` VPC-private `/_edge/health\|stats\|version\|slug_seen` mgmt surface, per brief 02), CF viewer-request JS | none (assets) | **done** |
| 5 — wiring + setup | `Setup__*`: IAM roles, CF distribution + origin group + ACM wildcard, Edge Waker deploy via `sg aws lambda`, `proxies.<parent>` zone; deploy-via-pytest | live AWS | |
| 6 — `sg edge_bench` harness | the doc-05 CLI: primitive/flow/failure scenarios, structured JSON, local + aws-bench targets, acceptance thresholds | local + AWS | |

# Test rig & acceptance (doc 05)

`sg edge_bench <scenario>` with structured JSON traces and explicit thresholds.
Phase-1 in-scope scenarios: P-01/03/05/06/07/10/11, F-01, F-06, X-04/05/10/12.
Local docker-compose stack covers everything except the AWS-timing scenarios
(P-05 CF DNS refresh, P-06 origin failover). Fail-fast, no retries.

# What we are explicitly NOT doing in Phase 1

- No vault target in the loop (static diagnostic page short-circuits routing).
- No proxy cert (plain HTTP), no sidecars (Vector/CW agent/heartbeat) — Phase 3.
- No auto-scaling (static proxy count) — Phase 3.
- No changes to the existing Vault Waker (`sg va` / `sg vp`) — Phase 2.
- No changes to any existing `sg *` command — the whole spec is additive.
