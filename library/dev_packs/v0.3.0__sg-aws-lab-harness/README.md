---
title: "sg aws lab — Dev Briefing Pack (post-v2)"
file: README.md
author: Architect (Claude)
date: 2026-05-17 (rev 2 — after dev merge)
repo: SGraph-AI__Service__Playwright @ dev (current root version: v0.2.27)
status: PROPOSED — no code yet. For human ratification before Dev picks up.
sequencing: POST-V2. Lands AFTER v2 vault-publish (plan: v0.2.23) ships its phases 2a/2b.
parent:
  - team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/README.md
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/README.md
related:
  - library/docs/cli/sg-aws/README.md                                          # user-facing surface that exists today
  - team/comms/plans/v0.2.28__sg-credentials-deferred-work.md                  # AWS session machinery this pack rides on top of
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md   # lab-brief compliance corrections
feature_branch: claude/aws-primitives-support-NVyEh
---

# `sg aws lab` — Dev Briefing Pack

A **measurement harness** for AWS-side behaviour: ~24 named experiments that turn the v2 vault-publish brief's assumptions about Route 53, CloudFront, and Lambda into measured facts. Each experiment provisions tiny throwaway resources, measures one specific behaviour, and tears down whether it passes, fails, or is `Ctrl-C`-ed.

> **PROPOSED — does not exist yet.** No code in `sgraph_ai_service_playwright__cli/aws/lab/` today. This is the briefing pack only.

> **Post-v2 sequencing.** Per Dinis's 2026-05-17 decision (v0.2.23 plan, Q1): v2 vault-publish ships FIRST. The lab harness lands AFTER v2 phases 2a/2b have shipped `sg aws cf` and `sg aws lambda`. Lab phases P0+P1 (DNS-only) CAN ship in parallel with v2 if there's developer capacity — they need no v2 deliverable.

---

## Why this revision exists (read this if you saw rev 1)

Rev 1 of this pack (committed 2026-05-17 in `v0.2.28__sg-aws-lab-harness/`) made three assumptions that **conflict with decisions already in `dev`**:

1. **It claimed v0.2.28** — but v0.2.28 is the `sg credentials` deferred work (`team/comms/plans/v0.2.28__sg-credentials-deferred-work.md`). Renamed to `v0.3.0__sg-aws-lab-harness/`.
2. **It folded `sg aws cf` / `sg aws lambda` primitive expansion into the lab milestone** — but the v0.2.23 vault-publish plan (`03__delta-from-lab-brief.md §B.5`) already decided those expansions belong to vault-publish phases 2a/2b, not the lab. Decisions #8 and #9 of rev 1 are **removed**.
3. **It assumed lab and v2 could ship in parallel** — but v0.2.23 Q1 decided **sequential, v2 first**. Critical-path diagram rebuilt accordingly.

Rev 2 also:
- Routes lab AWS calls through `Sg__Aws__Session.from_context().boto3_client_from_context()` (the v0.2.28 Phase D seam), not bare boto3 (decision #6 updated).
- Marks open Qs 1/4/6/11/14 as RESOLVED by the v0.2.23 plan.
- Cites `03__delta-from-lab-brief.md` deltas B.1-B.7 in every agent brief so Sonnet sub-agents don't replicate the lab-brief's CLAUDE.md compliance errors.
- Updates reality-doc and catalogue references to the new domain tree / 8-shard layout.

---

## One-paragraph summary

The v2 vault-publish brief leans on five claims about AWS behaviour — wildcard-vs-specific Route 53 routing, INSYNC propagation timing, CloudFront origin-error semantics, Lambda cold-start latency, and "Lambda exits the data path within one TTL". None of these are measured today. This pack proposes `sg aws lab` — a Typer surface mirroring `sg aws dns` — that hosts ~24 named experiments. The harness reuses every existing AWS primitive in this repo (`Route53__AWS__Client`, `CloudFront__AWS__Client`, `Lambda__AWS__Client`, `ACM__AWS__Client`, plus the v0.2.28 `Sg__Aws__Session` seam) and adds three layers of cleanup safety so it never leaks. Lab phases P0+P1 (DNS-only) ship as soon as the harness foundation is in place; P2 (Lambda) and P3 (CloudFront) wait for v2 vault-publish phases 2b / 2a to land the `sg aws cf` and `sg aws lambda` expansions; P4 (composite) closes the loop.

---

## Source documents

| Source | Authority | Use for |
|--------|-----------|---------|
| `team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/` (9 files) | **Architect brief — the design** | Component decomposition, experiment catalogue, safety story, module layout. The ground truth for *what* the harness does. |
| `team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/` (9 files) | **v2 plan with 17 resolved decisions** | Especially `03__delta-from-lab-brief.md` (lab-brief compliance corrections, B.1-B.7) and `08__decisions-applied.md` (decisions that already settle some of our open questions) |
| `team/comms/plans/v0.2.28__sg-credentials-deferred-work.md` | Credentials/AWS-session plan | The `Sg__Aws__Session` seam this pack rides on top of |
| `library/docs/cli/sg-aws/` | User-facing reference | What `sg aws *` does today (the substrate the lab measures against) |

If this pack contradicts any of those, **the source wins** — open an Architect-review request, do not silently diverge.

---

## File index

| # | File | Purpose |
|---|------|---------|
| 00 | this README | Status, locked decisions, sign-off, sequencing |
| 01 | [`01__scope-and-architecture.md`](01__scope-and-architecture.md) | Five questions, four pillars, module shape — the *what* |
| 02 | [`02__common-foundation.md`](02__common-foundation.md) | The shared scaffold every sub-agent builds on (must land first) |
| 03 | [`03__sonnet-orchestration-plan.md`](03__sonnet-orchestration-plan.md) | **The Sonnet sub-agent orchestration plan — the centrepiece** |
| 04 | [`04__agent-A__dns-experiments.md`](04__agent-A__dns-experiments.md) | Sonnet Agent A — DNS experiments (P0+P1). Ready to fire as soon as Foundation merges. |
| 05 | [`05__agent-B__lambda-experiments.md`](05__agent-B__lambda-experiments.md) | Sonnet Agent B — Lambda experiments (P2). **Waits for v2 phase 2b** (`sg aws lambda` expansion). |
| 06 | [`06__agent-C__cloudfront-experiments.md`](06__agent-C__cloudfront-experiments.md) | Sonnet Agent C — CloudFront experiments (P3). **Waits for v2 phase 2a** (`sg aws cf` expansion). |
| 07 | [`07__agent-D__transition-experiments.md`](07__agent-D__transition-experiments.md) | Sonnet Agent D — composite experiments (P4). Lands after A+B+C. |
| 08 | [`08__agent-E__viewer-and-renderers.md`](08__agent-E__viewer-and-renderers.md) | Sonnet Agent E — viewer + diff + HTML (P5). Fully independent. |

---

## Locked decisions (rev 2)

These are settled. If any seems wrong, raise an Architect-review request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **New top-level `sg aws lab` namespace** under `sgraph_ai_service_playwright__cli/aws/lab/` — mirrors `sg aws dns` shape (cli / service / schemas / enums / primitives / collections folders). | "Same shape as everything else." |
| 2 | **No temp boto3 wrappers.** Lab phases P0+P1 (DNS-only) ship first using `Route53__AWS__Client`. Lab phases P2 (Lambda) and P3 (CloudFront) WAIT for vault-publish phases 2b/2a to ship the expanded primitives, then use the real clients. No `Lab__CloudFront__Client__Temp` / `Lab__Lambda__Client__Temp` / no `P-Swap` PR. (Per delta `B.5`.) | Avoids the "build temp clients, delete them" dance. |
| 3 | **Three independent cleanup layers + TTL-stamped tags.** Resource ledger + atexit/signal handlers + tag-driven leak sweeper + `sg:lab:expires-at` 1-h default. **No experiment may leak.** Lab safety story stays in lab — **do NOT generalise it into vault-publish** (per delta `B.7`). | Hard guarantee from lab-brief §4. |
| 4 | **Read-only by default.** Mutations gated by `SG_AWS__LAB__ALLOW_MUTATIONS=1`. Tier-2 also needs `--tier-2-confirm`. | Same gate pattern as the rest of `sg aws *`. |
| 5 | **All A-record VALUES restricted to TEST-NET-1/2/3** (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) unless `--force-real-ip`. | Removes "lab record accidentally points at someone's production IP" failure mode. |
| 6 | **All lab AWS calls route through `Sg__Aws__Session.from_context().boto3_client_from_context(...)`** — the v0.2.28 Phase D seam. Falls through to bare boto3 when no role is set (behaviour-preserving for unconfigured operators); honours the active role (e.g. `sg --as lab ...`) when one is set. The existing per-service `*__AWS__Client.client()` methods (`Lambda__AWS__Client`, `CloudFront__AWS__Client`, `Route53__AWS__Client`, etc.) still call bare `boto3.client(...)` today — Phase D migrated only the per-resource `ec2_client/ssm_client/iam_client` seams across 62 files. Per-service-client migration is tracked in the v0.2.28 plan §3.4 as ongoing. The lab inherits the role-aware credentials, CloudTrail-correlatable session names, and audit-log integration as those clients migrate. **Platform caveat:** the keyring backend is macOS-only today; on Linux CI workers the seam falls through to bare boto3 (no role-awareness). See `02__common-foundation.md §8`. | One seam to inherit from; pragmatic about the in-progress migration. |
| 7 | **Type_Safe + per-class-file + empty `__init__.py`** everywhere. **Specifically:** no `Set__Str`, no `Dict__Str__Str`, no `Dict__Str__Int` (use `Type_Safe__Dict__Safe_Str__Safe_Str` etc.); runner injected at `setup` time as a field, not per-call (per delta `B.1`, `B.2`, `B.4`). **File names match class names exactly** — no `E01__zone_inventory.py` prefixing; experiment files are e.g. `Lab__Experiment__Zone_Inventory.py` per CLAUDE.md rule #21 (per delta `B.3`). | CLAUDE.md rules #1, #3, #20, #21, #22; lab-brief deltas B.1-B.4. |
| 8 | **Per-Sonnet-agent branches off `claude/aws-primitives-support-NVyEh`.** Each opens its own PR to the integration branch; integration merges to `dev` once all five are reviewed. | Bounded blast radius; parallel reviews. |

(Rev 1's decisions #8 and #9 — folding `sg aws cf` / `sg aws lambda` primitive expansion into the lab milestone — are **REMOVED**. Those expansions belong to vault-publish phases 2a/2b per the v0.2.23 plan.)

---

## Open questions — what changed

The lab-brief's `08__open-questions.md` listed 15 open questions. Several were resolved by the v0.2.23 vault-publish plan. Updated status:

| Q from lab-brief | Status | Source |
|------------------|--------|--------|
| **Q1 — which zone for mutating experiments?** | **RESOLVED.** Post-v2, lab gets its own delegated zone (`lab.sg-labs.app` or similar) with its own wildcard cert. Pre-v2, lab P0+P1 runs against `sg-compute.sgraph.ai` under `lab-*` name prefix. | v0.2.23 plan Q15-Q17 |
| Q2 — single AWS account or shared? | Architect rec: share, plus `Lab__Safety__Account_Guard` + dedicated `lab` role via `sg credentials`. Operator decision. | unchanged |
| Q3 — default TTL on lab-tagged resources? | Architect rec: 1 h, `--ttl` override. Operator decision. | unchanged |
| **Q4 — where do lab-minted ACM certs live?** | **RESOLVED.** Post-v2, lab uses its own wildcard cert in the lab zone (Q1). Pre-v2, lab P0+P1 needs no cert (DNS-only). | v0.2.23 plan Q7, Q15-Q17 |
| Q5 — 6 or 8 public resolvers? | Architect rec: 6 (smart-verify subset), `--full-set` flag. Operator decision. | unchanged |
| **Q6 — Function URL auth NONE vs AWS_IAM?** | **RESOLVED.** v2 confirmed `auth_type='NONE'`; lab follows the same pattern. | v0.2.23 plan Q8 |
| Q7 — share resources across runs? | Architect rec: per-run in P3, revisit B as P-Followup. | unchanged |
| Q8 — `.sg-lab/` location? | Architect rec: repo-root, `SG_AWS__LAB__HOME` override. | unchanged |
| Q9 — real-AWS tests in CI? | Architect rec: never initially; on-demand via `workflow_dispatch` once a baseline exists. | unchanged |
| Q10 — universal `--repeat N`? | Architect rec: per-experiment opt-in. | unchanged |
| **Q11 — aws-vault session expiry mid-run?** | **RESOLVED.** `Sg__Aws__Session.from_context()` caches per `(role, region, access_key_fingerprint)` with refresh window. Rotation invalidates the cache automatically (v0.2.28 plan Q6). | v0.2.28 plan §3.4 + Q6 |
| Q12 — naming convention? | Architect rec: per the resource-pattern table in lab-brief 08 Q12. | unchanged |
| Q13 — reuse `Stack__Naming` or new `Lab__Naming`? | Architect rec: separate `Lab__Naming`. | unchanged |
| **Q14 — `sg vault-publish lab` sub-command?** | **RESOLVED.** No. Labs are platform-level, stay under `sg aws lab`. | v0.2.23 plan structure |
| Q15 — what does v2 "validate Phase 0" mean? | **PARTIALLY RESOLVED.** v0.2.23 Q6 marks v2 Phase 0 as already COMPLETED 2026-05-17. The lab's first acceptance run (E10/E11/E12 against the lab zone, post-v2) becomes a baseline measurement, not a v2 gate. | v0.2.23 plan Q6 |

Open: Q2, Q3, Q5, Q7, Q8, Q9, Q10, Q12, Q13 — Architect has recommendations; operator decision needed before P1/P2/P3.

---

## Critical-path sign-off (Architect → Dev)

Before any Sonnet sub-agent picks up its slice:

- [ ] All 8 locked decisions accepted
- [ ] Outstanding open questions (Q2, Q3, Q5, Q7, Q8, Q9, Q10, Q12, Q13) ruled on
- [ ] `02__common-foundation.md` reviewed by Dev — confirms it can be one PR
- [ ] `03__sonnet-orchestration-plan.md` reviewed — agent boundaries are independent
- [ ] `03__delta-from-lab-brief.md` (B.1-B.7) read by every agent before they start
- [ ] Feature branch `claude/aws-primitives-support-NVyEh` is current with `dev`
- [ ] AppSec has reviewed the safety story and the TEST-NET restriction
- [ ] **v2 vault-publish phase 2a status confirmed** (gates Agent C)
- [ ] **v2 vault-publish phase 2b status confirmed** (gates Agent B)

---

## Pack-level "what success looks like"

When this milestone closes:

1. **`sg aws lab list`** shows ~24 experiments across 4 categories (DNS, Lambda, CloudFront, transition).
2. **`SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run propagation-timeline`** measures Route 53 propagation across 8 public resolvers with full ledger-based cleanup.
3. **`sg aws lab sweep`** finds and removes any leaked lab resources from a crashed previous session.
4. **Q1 + Q2 from the v2 brief are answered with numbers** (DNS-only experiments, no CF/Lambda mutations needed — these can ship pre-v2).
5. **The kill-9 safety acceptance test** (lab-brief §4.8) passes for every resource type.
6. **The lab acts as a regression-detection harness** for `sg aws cf` and `sg aws lambda` — a future behavioural change there shows up as a diff in lab run results.

---

## Status updates

| Date | Note |
|------|------|
| 2026-05-17 | Pack rev 1 filed at `v0.2.28__sg-aws-lab-harness/`. |
| 2026-05-17 | Pack rev 2 filed at `v0.3.0__sg-aws-lab-harness/` after `dev` merge — rev 1 conflicted with v0.2.28 credentials slot, the v0.2.23 vault-publish plan's primitive-expansion ownership, and the v2-first sequencing decision. See "Why this revision exists" above. Pack now consistent with `dev`. |
