---
title: "Vault-Publish Spec — v2 Brief (Architect)"
file: README.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-subdomain-workflow-bRIbm (v0.2.22 line)
status: BRIEF — no code yet, pending human ratification before Dev picks up.
supersedes: library/dev_packs/v0.2.11__vault-publish/
parent: team/humans/dinis_cruz/claude-code-web/05/14/01/v0.2.6__arch-plan__vault-app-stack__v2-delta.md
---

# Vault-Publish Spec — v2 Brief

A subdomain-publishing flow for `<slug>.sg-compute.sgraph.ai` that lights up an EC2 vault-app stack on demand and tears it back down when idle. Designed as a **`sg_compute_specs/vault_publish/` spec**, peer of `vault_app` / `playwright` / `mitmproxy`. Most of it composes existing primitives; only two new SG/Compute capabilities (`sg aws cf` + `sg aws lambda`) and one small extension to the existing vault-app spec (`stop` / `start`) are actually new.

---

## Read order

| # | File | What it covers |
|---|------|----------------|
| 01 | [`01__intent.md`](01__intent.md) | What we are trying to do; the cold-path / warm-path architecture; ASCII diagrams; the DNS-swap trick |
| 02 | [`02__what-exists-today.md`](02__what-exists-today.md) | Inventory of what is already in the repo, in `osbot-aws`, and in `osbot-utils` that this spec composes |
| 03 | [`03__sg-compute-additions.md`](03__sg-compute-additions.md) | What we add to SG/Compute **outside** the spec: `sg aws cf`, `sg aws lambda`, `sg vault-app stop` / `start` |
| 04 | [`04__vault-publish-spec.md`](04__vault-publish-spec.md) | What lives **inside** `sg_compute_specs/vault_publish/`: slug rules, registry, glue, the waker Lambda handler |
| 05 | [`05__implementation-phases.md`](05__implementation-phases.md) | Phased rollout: 0 (validate today) → 1 (stop/start) → 2 (CF + Lambda + Waker) → 3 (Fargate) |

---

## Two decisions this brief locks in

1. **Vault-publish is a spec, not a top-level package.** It lives at `sg_compute_specs/vault_publish/`, peer of `sg_compute_specs/vault_app/`. The top-level `vault_publish/` package on `claude/review-subdomain-workflow-bRIbm` (commits `c184867` + `23c2800` + `2335cee`) **does not get merged.** Only the slug-validation pieces (`Safe_Str__Slug`, `Slug__Validator`, `Reserved__Slugs`, their tests) get ported into the new spec. Everything else (the manifest interpreter, the signature verifier, the bespoke instance manager) was designed against a model that no longer applies.
2. **The old `library/dev_packs/v0.2.11__vault-publish/` pack is superseded.** Its core thesis (CloudFront + bespoke manifest interpreter + bespoke signing scheme + per-slug EC2 wake Lambda) was written before the `sg vault-app` and `sg aws dns` work landed. It should be marked `SUPERSEDED — see this brief` and left in place for archival.

---

## TL;DR

```
PHASE 0  (validate today)      no new code; `sg vault-app create --with-aws-dns` works
PHASE 1a (small)                add `sg vault-app stop` / `start` + re-run auto-DNS on start
PHASE 1b (medium)               scaffold sg_compute_specs/vault_publish/ + SSM slug registry
PHASE 2a (medium)               add `sg aws cf`     primitive (boto3 CloudFront wrapper)
PHASE 2b (small)                add `sg aws lambda` primitive (wraps osbot_aws.Deploy_Lambda)
PHASE 2c (medium)               write the Waker Lambda handler under the spec
PHASE 2d (small)                wire it all together via `sg vault-publish bootstrap`
PHASE 3   (later)               Endpoint__Resolver__Fargate — same Waker, different resolver
```

The bulk of phase 2 is the `sg aws cf` primitive (about 12 files) and the Waker handler (about 8 files). Everything else is either glue or already done.
