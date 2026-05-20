---
title: SG/Edge — implementation plan (Phase 1, codebase-grounded)
version: v0.2.37
date: 2026-05-20
status: plan / in-progress
role: Dev
audience: implementing engineer (or next Claude thread) picking up SG/Edge
related:
  - team/humans/dinis_cruz/briefs/05/20/sg-edge__01-solution-overview.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge__02-edge-fleet.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge__03-targets.md
  - team/humans/dinis_cruz/briefs/05/20/sg-edge__04-commercial-angles.md
prior:
  - sg_compute_specs/vault_publish/   (the Vault Waker — proven analogue)
---

# Why this plan exists

The four `sg-edge__*` briefs (05/20) describe a central edge tier — CloudFront +
ACM wildcard → OpenResty proxy fleet → vault targets, coordinated by two Wakers,
with DNS-as-registry and a single S3 lock. The briefs were written by an agent
without deep knowledge of this codebase, so they describe components in the
abstract (e.g. "SSM Run Command readiness polling", "RunInstances", "Route 53
A-record writes").

This plan re-grounds the design in what already exists. The headline: **almost
every AWS primitive SG/Edge needs already ships as a `sg aws *` module.** The
genuinely-new code surface is small. We build on the existing surface, we do not
reinvent it.

# Component → existing capability map

| Brief component | What it needs | Already exists | New work |
|---|---|---|---|
| CloudFront + wildcard ACM | TLS terminator, wildcard cert | `sg aws cf` (`CloudFront__AWS__Client`, `CloudFront__Distribution__Builder`, `ensure_distribution`, `wait_deployed`), `sg aws acm` (`ACM__AWS__Client`, validation records) | Edge-specific distribution config (alias `*.<parent>`, origin group) |
| CloudFront Function (Host preserve, slug extract) | CF Function CRUD | `CloudFront__Function__AWS__Client` (`create`, `publish`, `attach_function_to_distribution`) | The viewer-request JS source (co-located, per decision) |
| CF origin group failover (primary=proxies, secondary=Edge Waker) | failover origin config | **`CloudFront__Origin__Failover__Builder` already exists** | wire primary/secondary for the edge |
| Edge Waker Lambda + Function URL | deploy Lambda, public Fn URL | `sg aws lambda` (`deploy_from_folder`, `ensure_function_url`, `ensure_public_invoke_permission`) + `vault_publish/lambdas/waker/` pattern (`Waker__Handler`, `lambda_entry`, `Warming__Page`) | Edge Waker handler + loading page |
| Proxy fleet launch | RunInstances, security groups | `sg aws ec2` (`create_instance`, `create_stack`, `create_security_group`, `authorize_security_group_ingress`, `describe_instance`) | OpenResty user-data + edge SG |
| `proxies.<parent>` A records (fleet membership) | Route 53 A CRUD | `sg aws dns` (`create_record`, `delete_record`, `batch_delete_records`, `list_records`, `get_record`, `resolve_zone_for_fqdn`, `smart_verify`) | edge-scoped record helpers |
| `_sg.<slug>` TXT records (routing registry) | Route 53 TXT CRUD | same `sg aws dns` client (`Enum__Route53__Record_Type` covers TXT) | `SG_Edge__TXT__Builder` (compose/parse v=1) |
| Edge Waker / proxy IAM roles | role + inline policy | `sg aws iam` (`create_role`, `put_inline_policy`, `IAM__Trust_Policy__Builder`) | the two scoped policy docs |
| S3 boot lock (`If-None-Match`) | conditional create-once write | `sg aws s3` (`create_bucket`, `put_object`, `head_object`, `get_object_body`) — supports `IfMatch` only | **add `if_none_match` to `put_object`** (the one true new primitive) |
| Readiness polling | proxy "is it up yet?" | `vault_publish` polls over HTTP (no SSM module exists) | poll `/_edge/health` over HTTP — adopt proven pattern, drop SSM |
| Log shipping target | CloudWatch Logs | `sg aws logs` | Vector config on proxy |

## Two deliberate departures from the briefs

1. **No SSM.** The briefs assume `ssm:SendCommand` for readiness polling. There
   is no `sg aws ssm` module, and `vault_publish` already proves readiness can be
   polled over HTTP against the instance's health endpoint. We poll
   `/_edge/health` over HTTP. Bonus: the proxy IAM role needs no `ssm:*` grant,
   keeping blast radius minimal (which the brief itself wants).

2. **S3 `If-None-Match` is the only new AWS primitive.** `S3__AWS__Client.put_object`
   currently supports `IfMatch` (update-if-unchanged) but not `If-None-Match`
   (create-if-absent). The boot lock needs create-if-absent. We add an
   `if_none_match` parameter — a few lines, fully unit-testable against the
   existing S3 client seam.

# Decisions (adopted from brief open questions)

Per owner sign-off (2026-05-20), all five brief recommendations are the working
defaults:

1. **Proxy cert:** self-signed, regenerated at boot. No secret management; CF does
   not verify the origin cert.
2. **TXT TTL:** 30s (matches OpenResty `shared_dict` cache TTL). Vault Waker
   verifies the record resolves before reporting ready.
3. **CloudFront Function location:** co-located in the edge module
   (`sg_compute_specs/edge/cloudfront_function/`), since it co-evolves with the
   proxy.
4. **Scale-up trigger:** active vault count (`ceil(active_vaults / N)`), simplest
   and aligns the scale story end-to-end.
5. **Log redaction:** at the source (proxy-side Vector `transforms.remap`),
   matching current `send.sgraph.ai` practice.

# Package layout

New spec sibling to `vault_publish`, modelled on it:

```
sg_compute_specs/edge/
  primitives/    Safe_Str__Edge__Parent_Domain, Safe_Int__Edge__Unix_Ts,
                 Safe_Int__Edge__TXT_Version, Safe_Int__Edge__Cycle_Count
  enums/         Enum__Edge__Backend__Type, Enum__Edge__Fleet__State
  schemas/       Schema__Edge__TXT__Record, Schema__Edge__Fleet__State
  collections/   List__Safe_Str__IP__Address
  service/       SG_Edge__TXT__Builder            (Slice 1, this commit)
                 SG_Edge__Boot__Lock              (Slice 2)
                 SG_Edge__Fleet__Manager          (Slice 3)
  cloudfront_function/  viewer-request JS         (Slice 4)
  user_data/     OpenResty + sidecar boot script  (Slice 4)
  lambdas/edge_waker/   Waker__Handler, lambda_entry, Warming__Page  (Slice 5)
  setup/         Setup__S3_Lock / Setup__IAM / Setup__CF / Setup__Lambda / Setup__DNS  (Slice 6)
  tests/         co-located, no mocks
```

Tests stay AWS-call-free where possible; AWS-touching service classes take an
injected client seam (the `vault_publish` `_ec2_factory` pattern) so unit tests
run against in-memory fakes — no mocks, no patches.

# Phase 1 slice sequence

The briefs say build Phase 1 (the edge tier, in isolation) first — the risky
mechanics behind a static-site rig, no vault target in the loop. Within Phase 1:

| Slice | Scope | AWS? | Status |
|---|---|---|---|
| **1 — typed foundation** | primitives, enums, `Schema__Edge__TXT__Record`, `Schema__Edge__Fleet__State`, `SG_Edge__TXT__Builder`, collections; unit tests | none | **this commit** |
| 2 — boot lock | `if_none_match` on `S3__AWS__Client.put_object`; `SG_Edge__Boot__Lock` (acquire/read/update/release over the S3 client seam) | S3 (seam) | next |
| 3 — fleet manager | `SG_Edge__Fleet__Manager` — state transitions, scale/teardown math (`ceil(active/N)`, zero_streak), DNS A-record membership via `sg aws dns` | EC2/DNS (seam) | |
| 4 — proxy rig | OpenResty static-diagnostic user-data, self-signed cert at boot, sidecars (Vector/CW agent/heartbeat), CF Function JS | none (assets) | |
| 5 — Edge Waker | Lambda handler + Function URL + loading page, modelled on `vault_publish/lambdas/waker/`; HTTP readiness poll | Lambda (seam) | |
| 6 — wiring + setup | `Setup__*` orchestration: S3 lock bucket, IAM roles, CF distribution + origin group + ACM wildcard, Edge Waker deploy, `proxies.<parent>` zone; deploy-via-pytest | live AWS | |

Phase 2 (vault targets behind the edge) and Phase 3 (production hardening) are
out of scope for this plan and tracked separately.

# Test rig (Phase 1 exit criteria)

From brief 01 — what the static-site rig must let us hammer: CF failover timing,
concurrent cold-cold triggers (S3 lock prevents duplicate launches), EC2 boot
under stress, mid-boot failure, proxy kill during traffic, aggressive
teardown/boot cycles, DNS propagation at CF POPs, end-to-end cold-cold UX.

# What we are explicitly NOT doing in Phase 1

- No vault target in the loop (static diagnostic page short-circuits routing).
- No changes to the existing Vault Waker (`sg va` / `sg vp`) — Phase 2.
- No removal of the traditional CF + ALB + always-on path — it coexists.
