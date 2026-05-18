---
title: "Status update — what has landed since the brief was written (v0.2.29)"
file: 07__status-update.md
author: Claude (Opus 4.7)
date: 2026-05-18 (UTC hour 19)
version: v0.2.29
parent: README.md
supersedes_sections_in: 06__decisions-and-tradeoffs.md
---

# Status update — 2026-05-18 hour 19

The brief was written at hour 11 today. By hour 19, several recommendations
have already landed on branch `claude/waker-debug-clean-bRIbm`. This file
annotates each recommendation with its current status so future readers
don't re-do work that's already done.

## Status legend

- ✅ **DONE** — recommendation fully implemented and tested
- 🟡 **PARTIAL** — some of the recommendation is in; remainder noted
- ❌ **PENDING** — not started yet
- ⚠ **DIVERGED** — implementation took a different (and reasonable) path

## Recommendations matrix — updated

| Brief recommendation | Brief verdict | Status as of 19:00 | Commit / notes |
|---|---|---|---|
| Rename `vault-publish` → `ephemeral-ec2`? | No, keep name | ✅ DONE (no rename) | n/a |
| Extract a `Workload` seam internally | Yes | ❌ PENDING | `Schema__Vault_Publish__Entry` still has no `port`/`health_path`/`warming_label` fields |
| Lambda always returns warming HTML | No, default to reverse-proxy when IP known | ❌ PENDING | `Waker__Handler.handle()` still uses warming-HTML path; no port-reachability probe yet |
| Let's Encrypt approach | HTTP-01 via Lambda reverse-proxy | ❌ PENDING | `/.well-known/acme-challenge/*` not handled; depends on reverse-proxy |
| `sg vault-publish eval` CLI | Yes, mirror setup-check pattern | ❌ PENDING | No `eval/` package exists yet |
| Per-slug `health_probe_path` in SSM entry | Yes | ❌ PENDING | Bundled with Workload seam work |

## Implementation-review fixes from `01__implementation-review.md:189-208`

| Fix | Status | Notes |
|---|---|---|
| Statement-level IAM drift detection | ✅ DONE | `Setup__IAM._stmt_key()` + `missing_statements`/`extra_statements` (commit `0ea8659` lineage) |
| Trust-policy validation | ✅ DONE | `Schema__Setup__IAM__Report.trust_policy_ok` |
| Add `name: str` field to `Schema__IAM__Policy` | 🟡 PARTIAL | Field added; `_find_inline_policy` uses exact name match (no dead `not p.name` fallback) |
| Drop unused `create_resp` variable | ❌ PENDING | Minor cleanup |
| `status()` returns Type_Safe schema not dict | ❌ PENDING | Still returns `dict` |
| CLI smoke test via `typer.testing.CliRunner` | ❌ PENDING | No setup CLI smoke tests yet |

## Things the brief did not anticipate but happened anyway

These landed during the same window and are worth noting:

| Work | Commit | Why it happened |
|---|---|---|
| Phase B2/B3 setup areas (Lambda + CF + ACM + DNS) | `0ea8659` | User asked for them before decoupling; brief had this as "next 2-5 days" |
| `sg vp setup check/create/update/delete` global verbs | `0ea8659` | Mirror of `Setup__IAM` shape extended across all 5 areas |
| Removed `sg vp bootstrap` command | `0ea8659` | Superseded by `sg vp setup create` (brief didn't address it directly) |
| Waker docs at `/__waker__/docs` + `openapi.json` | `e1b3982` | Operability addition; not in brief |
| Rich diagnostic 404 page | `e1b3982` | Operability addition; not in brief |
| osbot_aws.Parameter.value() workaround | `e4e52a9` | Upstream `Misc.get_value` was removed; not anticipated |
| Route 53 `\052` wildcard normalisation | `a41098c` | Discovered during DNS check |
| `Setup__DNS` accepts A-alias wildcards (not just CNAME) | `1b98093` | Existing infra uses A-alias; brief assumed CNAME |
| `Lambda__Deployer` region pinning | `ecc8170` | Region mismatch caused `create_function(Role='')` validation error |

## Revised sequencing (replaces `06__decisions-and-tradeoffs.md:119-131`)

Original timeline assumed Phase B2/B3 would be the next chunk. Since
those are already done, the next chunk is:

1. **0.5d** — Implementation-review cleanup (4 remaining items above)
2. **1.0-1.5d** — Decoupling: add `port`/`health_path`/`warming_label` to
   `Schema__Vault_Publish__Entry`; thread through `Endpoint__Resolver__EC2`,
   `Waker__Handler._health_ok`, `Warming__Page`
3. **1.5d** — Reverse-proxy: ACME path always-proxy + AUTO mode (proxy when
   port reachable); requires #2
4. **2.0d** — Eval CLI (`sg vp eval`); depends on #2 and partially on #3

Total ~5d remaining, much of #4 parallelisable with #3.

## Known limitation surfaced after the brief

The diagnostic 404 page revealed that **CloudFront strips the original viewer
`Host` header** when forwarding to a Lambda Function URL (Lambda URLs reject
mismatched Host headers, so CF rewrites Host to the origin's hostname). This
means `Slug__From_Host` never sees `aaaaaa.aws.sg-labs.app` — it only ever
sees `<lambda-url-hash>.lambda-url.eu-west-2.on.aws`.

This is **a real bug, not a brief item**. The fix needs:
- A CloudFront Function (viewer-request) that copies viewer `Host` →
  `X-Forwarded-Host` header before forwarding to origin
- `Slug__From_Host` updated to prefer `X-Forwarded-Host` when present

This is unrelated to the reverse-proxy decision but is a prerequisite for
**any** slug routing to work in production. It needs to be fixed before
the eval CLI can run end-to-end.

Tracking as part of the "decoupling + reverse-proxy" chunk — but it can
land independently as a small commit + CF Function update.
