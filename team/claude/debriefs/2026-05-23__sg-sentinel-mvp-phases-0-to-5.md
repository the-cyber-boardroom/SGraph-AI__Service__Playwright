---
title: "SG/Sentinel MVP — Phases 0–5 (edge guard: logging + blocking)"
date: 2026-05-23
status: COMPLETE
branch: claude/gracious-galileo-fNYWn
merged-to-dev: false
---

# SG/Sentinel MVP — Phases 0–5

## 1. Header

| Field | Value |
|-------|-------|
| Date | 2026-05-23 |
| Status | **COMPLETE** — 6 phases landed, 74 sentinel tests green (3 gated live/docker skip), full CLI suite 3311 green |
| Branch | `claude/gracious-galileo-fNYWn` |
| Role | Architect → Dev |
| Briefs | `team/humans/dinis_cruz/briefs/05/22/v0.27.59__arch-brief…` + `v0.27.60__dev-brief…` (+ the `sg-sentinel/` series) |

## 2. TL;DR for the next agent

1. **`sg sentinel` is a real top-level peer surface** (alias `sn`), mounted in `sg_compute/cli/Cli__SG.py`, living at `sgraph_ai_service_playwright__cli/sentinel/`.
2. **L1 decides + signals; L2 acts + writes.** One JS engine (`runtime/layer1/sentinel_l1.js`, CF-Functions-2.0-compatible, dependency-free) emits `Schema__Sentinel__Signal`; the Python L2 actor (`runtime/layer2/Sentinel__L2__Actor.py`) enforces (pass/403/404) and writes a `Schema__Sentinel__Log_Record` to a `Log__Sink` (InMemory / Local_FS / S3). L2 never re-evaluates rules.
3. **Three targets, one signal spine.** local-direct (node subprocess), local-docker (CF-env sim container), live AWS (CF Function on viewer-request + Lambda@Edge on origin-request, cache-disabled). The parity matrix is the definition of done.
4. **The single source of the engine is `sentinel_l1.js`.** `BANNED_IPS` is inlined from `rules.embedded.json` by `Sentinel__L1__Source` (local/docker) and the deployer (CF) — never edit a materialised copy.
5. **Live deploy is code-complete and unit-tested via in-memory doubles**, but never run live in this session (no AWS). The gated Phase-5 smoke + AWS-parity tests are the live acceptance checks.

## 3. What landed, per phase

| Phase | Delivered | Target |
|-------|-----------|--------|
| 0 | Package skeleton; 9 primitives, 4 enums, 7 schemas, 2 collections; `sg sentinel --help` + `sn` | — |
| 1 | `sentinel_l1.js` + 6 rules + `Sentinel__L1__Source` (node) + `rules list/show/test` | — |
| 2 | `Sentinel__L2__Actor`, `Log__Sink` (base/InMemory/Local_FS), `Signal__Codec`, local-direct harness; `local up/hit/down`, `logs`, `blocks` | **B** |
| 3 | Docker CF-env sim (Dockerfile + `server.node.js`), `Sentinel__Docker__Runtime/Harness`, `local --docker`, B↔C parity | **C** |
| 4 | `Sentinel__Deployer` (+`__In_Memory`), S3 sink, L@E `lambda_handler`, role profiles, `deploy create/destroy/teardown`, `status` | live code-complete |
| 5 | Three-target parity matrix (local-direct baseline runs) + gated live smoke | **A** + parity |

## 4. Shared `aws/*` extensions (each with an EXCEPTION header)

These were flagged by the pre-implementation review and built here:
- `CloudFront__AWS__Client.associate_lambda_edge / disassociate_lambda_edge / get_lambda_edge_associations` — `LambdaFunctionAssociations` had no coverage.
- `Lambda__Deployer.publish_version` — numbered version ARN (L@E rejects `$LATEST`).
- `S3__AWS__Client.delete_bucket / empty_bucket` — orphan-free teardown.
- `Enum__AWS__Surface.SENTINEL` — the tagging surface member.
- **`Schema__AWS__Role__Profile.trust_services`** + `AWS__Role__Profiles.service_trust_policy_document / trust_policy_for` + provisioner honouring it — the approved **option (a)**: lets a profile express a Lambda@Edge **execution-role** trust (`lambda` + `edgelambda`). This is a `_shared` contract change; signed off by the project lead.
- New test doubles: `CloudFront__Function__AWS__Client__In_Memory`; `publish_version` on the lambda fake; `delete_bucket` on the s3 fake.

## 5. Good failures (caught early by tests)

- **Default `Safe_Str` sanitises punctuation.** `Safe_Str('example.com')` → `example_com` (dot stripped), which failed the CF domain regex; and rule names/reasons lost hyphens/spaces. Fixed by dedicated permissive primitives (`Safe_Str__Sentinel__Path/Reason/Name/IP/…`) and using `Safe_Str__CF__Domain_Name` / `Safe_Str__AWS__ARN` where the value must round-trip. Caught immediately by construction/round-trip tests.
- **Numbered L@E version ARN (`…:function:name:N`) is rejected by `Safe_Str__Lambda__Arn`.** The deploy response field was switched to `Safe_Str__AWS__ARN` (allows the `:N` suffix). This is the brief's own gotcha, surfaced by the in-memory lifecycle test.
- **`unittest.skipUnless` on a plain class does not stop pytest running `setup_class`** — the docker parity test errored instead of skipping. Switched to `pytest.mark.skipif`. Also made `docker_available()` probe the daemon (`docker info`), not just the binary.
- **An empty mounted Typer sub-app breaks `sg --help`.** The root `Cli__Sentinel` needed a `@app.callback()` anchor in Phase 0 before any subgroup existed.

## 6. Bad failures / known gaps (explicit follow-ups)

- **Live Lambda@Edge packaging is not validated.** The deployer packages `runtime/layer2/` and templates `_sentinel_config.py`, but the full dependency zip (Type_Safe + the sentinel package) and the L@E code-size budget are only exercised by the gated Phase-5 smoke test — never run live here. **Next agent must run the live smoke before claiming Target A works.**
- **Per-resource AWS tagging is not wired.** `Enum__AWS__Surface.SENTINEL` exists, but the existing S3/CF/Lambda create paths don't thread tags through, so created resources are not `sg:*`-tagged yet. Consistent with current client capabilities; flagged for a follow-up that adds tagging to those clients.
- **`CloudFront__Function__AWS__Client` uses `boto3.client()` directly** (pre-existing convention drift vs `boto3_client_via_context`). Left as-is; noted so `sg credentials switch` behaviour on the CF-Function path is understood.

## 7. Test posture

- No mocks, no patches — real `*__In_Memory` subclasses with dict-backed fakes throughout.
- node-gated tests run in this environment (node v22 present); docker + live-AWS legs skip cleanly.
- `tests/unit/sgraph_ai_service_playwright__cli`: **3311 passed, 3 skipped** — no regressions from the shared changes (192 `aws/*` tests green).

## 8. How to use / test

See the testing manual: `team/humans/dinis_cruz/claude-code-web/05/23/17/sg-sentinel-testing-manual.md`.
