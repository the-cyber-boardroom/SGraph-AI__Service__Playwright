---
title: "Architect Plan — vault-publish-spec v2 (implementation, grounded in reality)"
file: README.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
repo: SGraph-AI__Service__Playwright @ dev (reality v0.1.140)
status: PLAN — no code, no commits. For human ratification before Dev picks up.
parent:
  - /tmp/vault-publish-brief/README.md
  - team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/README.md
supersedes:
  - library/dev_packs/v0.2.11__vault-publish/ (already declared SUPERSEDED by the v2 brief itself)
---

# Architect Plan — vault-publish-spec v2

A reality-grounded implementation plan for the v2 vault-publish brief at `/tmp/vault-publish-brief/`. Composes the lab-brief (`team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/`) as a separate but parallel measurement track.

This plan does **not** restate the brief. It cross-checks every component the brief proposes against the *actual* code in this repo and produces:

1. a re-use map (which existing class becomes the substrate for which brief concept),
2. corrections where the brief or lab-brief drift from project rules (`.claude/CLAUDE.md`),
3. a phased plan mapped onto the project's roadmap conventions,
4. a test strategy that obeys the no-mocks rule,
5. an explicit list of decisions the human must make before Dev starts.

---

## Reading order

| # | File | What it covers |
|---|------|----------------|
| 01 | [`01__grounding.md`](01__grounding.md) | Every major brief component: does it exist today? Cited from the codebase. PROPOSED items flagged per CLAUDE.md rule. |
| 02 | [`02__reuse-map.md`](02__reuse-map.md) | Concrete table: brief concept → existing file → action. Maximises re-use. |
| 03 | [`03__delta-from-lab-brief.md`](03__delta-from-lab-brief.md) | Where the lab-brief's proposed module shape collides with project rules; corrected shape. How the lab-brief slots alongside the vault-publish plan rather than into it. |
| 04 | [`04__phased-implementation.md`](04__phased-implementation.md) | Per-phase scope (files touched/created, tests, success criteria, risks). Mapped onto the v2 brief's Phase 0 → 2d while preserving the brief's own phasing labels. |
| 05 | [`05__test-strategy.md`](05__test-strategy.md) | No-mocks composition, in-memory fixtures to build, Chromium-gated tests (none here — vault-publish has no browser steps), AWS-gated integration tests. |
| 06 | [`06__open-questions.md`](06__open-questions.md) | Questions for the human; brief-vs-lab-brief contradictions; pre-Dev decisions. |
| 07 | [`07__domain-strategy.md`](07__domain-strategy.md) | Subdomain naming (`<slug>.<namespace>.sg-labs.app`), wildcard ACM cert per namespace, Route 53 record lifecycle, hosted-zone wiring, phase placement. Added after the user registered `sg-labs.app`. |

---

## Headline summary (TL;DR)

- **The brief is mostly composition over existing primitives.** ~80% of the surface either already exists (`sg vault-app`, `sg aws dns`, `osbot_aws.Parameter`, `osbot_aws.Deploy_Lambda`, `Route53__AWS__Client`, `Vault_App__Auto_DNS`) or is a thin Type_Safe wrapper around an `osbot-aws` helper.
- **Three real new pieces of net-new platform code:** (a) `sg aws cf` (the only large rock — ~24 files), (b) `sg aws lambda` (~16 files), (c) `sg_compute_specs/vault_publish/` itself (~30 production files, but most are small data classes).
- **Two small but load-bearing extensions:** (a) `sg vault-app stop` / `start` verbs + the "self-stop instead of terminate" user-data change, (b) a `ec2:StopInstances` policy line on the `playwright-ec2` IAM profile.
- **The lab-brief is not in the critical path of vault-publish v2.** It is a measurement harness. The plan keeps it as a sibling track that lands in parallel (P0+P1 of the lab cover the v2 brief's Phase 0), but the vault-publish implementation does not depend on the lab existing.
- **Three CLAUDE.md compliance corrections** are pulled out of the brief and lab-brief and re-cast into the plan: (i) raw `str` / `dict` defaults in the brief's example schemas get replaced by `Safe_Str__*` / `Type_Safe__Dict__*`; (ii) the brief's "manual one-time bootstrap" for ACM gets an explicit gated-mutation flag for any case where the spec mints a cert; (iii) the lab-brief's `Literal`-shaped enum hints get rewritten as `Enum__*` classes.

See `04__phased-implementation.md` for the per-phase deliverable list. See `06__open-questions.md` for the four blocking questions the human must answer before Dev starts.

---

## What this plan deliberately does NOT do

- **No production code.** No file under `sg_compute_specs/vault_publish/` or `sgraph_ai_service_playwright__cli/aws/cf/` exists yet, and this plan does not create any. Dev consumes the plan and writes the code.
- **No re-derivation of the brief's design.** The brief is the design; this plan is the *delta vs the codebase*.
- **No commitment to phases the brief defers.** Phase 3 (Fargate) and Phase 4 (private VPC) get a passing mention and otherwise stay out of scope, exactly as the brief intends.
- **No commitment to deleting the SUPERSEDED v0.2.11 dev-pack.** That archival decision is the Historian's; this plan flags only the *code-level* port: `Safe_Str__Slug` + `Slug__Validator` + `Reserved__Slugs` (note: no top-level `vault_publish/` Python package actually exists in this branch — see `01__grounding.md §2.2`, the brief is mis-citing a different branch).
