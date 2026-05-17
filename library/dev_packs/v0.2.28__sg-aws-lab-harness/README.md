---
title: "sg aws lab + primitives expansion — Dev Briefing Pack"
file: README.md
author: Architect (Claude)
date: 2026-05-17
repo: SGraph-AI__Service__Playwright @ dev (v0.2.26 line → targeting v0.2.28)
status: PROPOSED — no code yet. For human ratification before Dev picks up.
parent:
  - team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/README.md
related:
  - library/docs/cli/sg-aws/README.md          # user-facing surface that exists today
  - library/dev_packs/v0.2.11__vault-publish/  # the v2 brief whose assumptions this pack measures
  - team/comms/plans/                          # any open plans
feature_branch: claude/aws-primitives-support-NVyEh
---

# `sg aws lab` + primitives expansion — Dev Briefing Pack

A **measurement harness** (`sg aws lab`) plus a **targeted expansion of `sg aws cf` and `sg aws lambda`** to unlock the v2 vault-publish brief. The harness measures the AWS-side behaviour the v2 brief depends on; the primitive expansions are the mutation-capable wrappers the harness (and the v2 implementation) use under the hood.

> **PROPOSED — does not exist yet.** `sg aws lab` is a new top-level namespace; the expanded `sg aws cf` / `sg aws lambda` verbs are additions to existing namespaces. Cross-check against [`team/roles/librarian/reality/`](../../../team/roles/librarian/reality/README.md) before describing anything here as built.

---

## One-paragraph summary

The v2 vault-publish brief (`library/dev_packs/v0.2.11__vault-publish/`) leans on **five claims about AWS behaviour** — wildcard-vs-specific Route 53 routing, INSYNC propagation timing, CloudFront origin-error semantics, Lambda cold-start latency, and "Lambda exits the data path within one TTL". None of these are measured today. This pack proposes `sg aws lab` — a Typer surface mirroring `sg aws dns` — that hosts ~24 named experiments, each provisioning tiny throwaway AWS resources, measuring one specific behaviour, and tearing down whether the experiment passes, fails, or is `Ctrl-C`-ed. The harness depends on two new primitive surfaces (`sg aws cf` mutation verbs beyond what exists today; `sg aws lambda` deployment verbs) — those expansions are folded into this pack so the same v0.2.28 milestone delivers the measurement layer and the primitives it uses.

---

## Source briefs

This pack synthesises the 9-file Architect brief filed on 2026-05-16:

| Source file | Drives |
|-------------|--------|
| [`lab-brief/README.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/README.md) | This README |
| [`lab-brief/01__intent-and-principles.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/01__intent-and-principles.md) | `01__scope-and-architecture.md` |
| [`lab-brief/02__component-decomposition.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/02__component-decomposition.md) | `01__scope-and-architecture.md` |
| [`lab-brief/03__experiment-catalogue.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/03__experiment-catalogue.md) | per-agent briefs (`04`–`08`) |
| [`lab-brief/04__safety-and-cleanup.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/04__safety-and-cleanup.md) | `02__common-foundation.md` |
| [`lab-brief/05__module-layout.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/05__module-layout.md) | `02__common-foundation.md` |
| [`lab-brief/06__ui-and-visualisation.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/06__ui-and-visualisation.md) | `08__agent-E__viewer-and-renderers.md` |
| [`lab-brief/07__phasing.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/07__phasing.md) | `03__sonnet-orchestration-plan.md` |
| [`lab-brief/08__open-questions.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/08__open-questions.md) | Sign-off list (this file) |

The source briefs are **the ground truth.** Where this pack restates them it is for Dev convenience; if it contradicts them it is a bug — open an Architect-review request.

---

## File index

| # | File | Purpose |
|---|------|---------|
| 00 | this README | Status, summary, locked decisions, sign-off |
| 01 | [`01__scope-and-architecture.md`](01__scope-and-architecture.md) | Five questions, four pillars, module shape — the *what* |
| 02 | [`02__common-foundation.md`](02__common-foundation.md) | The shared scaffold every sub-agent must build on top of (must land first) |
| 03 | [`03__sonnet-orchestration-plan.md`](03__sonnet-orchestration-plan.md) | **The Sonnet sub-agent orchestration plan — the centrepiece** |
| 04 | [`04__agent-A__dns-experiments.md`](04__agent-A__dns-experiments.md) | Self-contained brief for Sonnet Agent A — DNS experiments (P0+P1) |
| 05 | [`05__agent-B__lambda-experiments.md`](05__agent-B__lambda-experiments.md) | Self-contained brief for Sonnet Agent B — Lambda experiments (P2) |
| 06 | [`06__agent-C__cloudfront-experiments.md`](06__agent-C__cloudfront-experiments.md) | Self-contained brief for Sonnet Agent C — CloudFront experiments (P3) |
| 07 | [`07__agent-D__transition-experiments.md`](07__agent-D__transition-experiments.md) | Self-contained brief for Sonnet Agent D — composite experiments (P4) |
| 08 | [`08__agent-E__viewer-and-renderers.md`](08__agent-E__viewer-and-renderers.md) | Self-contained brief for Sonnet Agent E — viewer + diff + HTML report (P5) |

---

## Locked decisions

These are settled. If any seems wrong, raise an Architect-review request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **New top-level `sg aws lab` namespace** under `sgraph_ai_service_playwright__cli/aws/lab/` — mirrors `sg aws dns` exactly (cli / service / schemas / enums / primitives / collections folders). | "Same shape as everything else." One layer per concern. |
| 2 | **The lab is the regression harness for the primitives it informs.** Once `sg aws cf` and `sg aws lambda` expand to cover what the harness needs, the harness deletes its `Lab__*__Client__Temp` boto3 wrappers in a single PR and continues running through the real primitives. Any behavioural drift then shows up as a diff in lab results. | Two deliverables for the cost of one. |
| 3 | **Three independent cleanup layers + TTL-stamped tags.** Resource ledger + atexit/signal handlers + tag-driven leak sweeper, with `sg:lab:expires-at` as a session-level backstop. **No experiment may leak.** | Hard guarantee from the source brief §4. |
| 4 | **Read-only by default. Mutations gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1`. Tier-2 also needs `--tier-2-confirm`.** | Same gate pattern as the rest of `sg aws *` (see `library/docs/cli/sg-aws/01__getting-started.md`). |
| 5 | **All A-record VALUES restricted to TEST-NET-1/2/3** (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) unless `--force-real-ip`. | Removes "lab record accidentally points at someone's production IP" failure mode. |
| 6 | **Every lab AWS call routes through `osbot-aws` or the existing `*__AWS__Client` classes** — the temp-boto3 wrappers (`Lab__CloudFront__Client__Temp`, `Lab__Lambda__Client__Temp`) are tagged for deletion the moment the primitive expansions ship. | CLAUDE.md rule #14. The temp clients are a documented, time-bound exception. |
| 7 | **Type_Safe everywhere, no Pydantic, no Literals, one class per file, empty `__init__.py`.** | CLAUDE.md rules #1, #3, #20, #21, #22. |
| 8 | **The `sg aws cf` primitive expansion lands as part of P3, NOT as a separate dependency.** Agent C delivers the CF experiments AND the `cf distribution update`, `cf distribution invalidate`, `cf tags` verbs needed for both Lab and v2-brief work. | Two birds, one PR. |
| 9 | **The `sg aws lambda` primitive expansion lands as part of P2, NOT as a separate dependency.** Agent B delivers Lambda experiments AND the `lambda <name> deploy-from-image`, `lambda <name> alias`, `lambda <name> permissions` verbs the v2 brief needs. | Same rationale as #8. |
| 10 | **Per-Sonnet-agent branches off `claude/aws-primitives-support-NVyEh`.** Each sub-agent opens its own PR to the integration branch; integration branch merges to `dev` once all five are reviewed. | Keeps blast radius bounded; allows reviews in parallel. |

---

## Critical-path sign-off (Architect → Dev)

Before any Sonnet sub-agent picks up its slice:

- [ ] All 10 locked decisions accepted by Dinis
- [ ] Open questions in `lab-brief/08__open-questions.md` answered (block P2/P3/P4 only — not P0/P1)
- [ ] `02__common-foundation.md` reviewed by Dev — confirms it can be one PR
- [ ] `03__sonnet-orchestration-plan.md` reviewed — agent boundaries are independent
- [ ] Feature branch `claude/aws-primitives-support-NVyEh` is current with `dev`
- [ ] AppSec has reviewed the safety story (`02__common-foundation.md §4`) and the TEST-NET restriction (`decision #5`)

---

## Pack-level "what success looks like"

A successful v0.2.28 milestone — three to four developer-days of Sonnet work — delivers:

1. **`sg aws lab list`** shows ~24 experiments across 4 categories (DNS, Lambda, CloudFront, transition).
2. **`SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E11`** measures Route 53 propagation across 8 public resolvers with full ledger-based cleanup.
3. **`sg aws lab sweep`** finds and removes any leaked lab resources from a previous crashed session.
4. **`sg aws cf distribution update / invalidate / tags`** and **`sg aws lambda <name> alias / permissions / deploy-from-image`** are available for v2-brief consumption.
5. **Q1 + Q2 from the v2 brief are answered with numbers** (DNS-only experiments, no CF/Lambda mutations needed).
6. **The kill-9 safety acceptance test** (lab-brief §4.8) passes for the DNS slice.

Phases 2–4 (Lambda, CF, transition experiments) can land **in parallel** to phase 1 once the common foundation is in place, then E27 (the full cold-path waterfall) closes the loop.

---

## Status updates

| Date | Note |
|------|------|
| 2026-05-17 | Pack filed by Architect, synthesising the 9-file lab-brief from 2026-05-16. Awaiting Dinis sign-off on decisions and open questions before Sonnet pickup. |
