---
title: "03 — Sonnet sub-agent orchestration plan"
file: 03__sonnet-orchestration-plan.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 03 — Sonnet sub-agent orchestration plan

How to ship v0.2.29 with **one Foundation PR followed by 8 parallel Sonnet sub-agents**, each driven from its own independently approvable sibling pack.

This is the centrepiece of the umbrella. The per-area briefs (`v0.2.29__sg-aws-<area>/README.md`) are the self-contained handoffs each Sonnet agent receives.

---

## 1. The shape

```
                  ┌──────────────────────────────────────┐
                  │   Agent 0 — Foundation               │
                  │   ~1 day, Sonnet, Opus-reviewed      │
                  │   Brief: 02__common-foundation.md    │
                  │   PR → claude/aws-primitives-…       │
                  └────────────────┬─────────────────────┘
                                   │ MERGED FIRST
                                   ▼
          ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┐
          ▼        ▼        ▼        ▼        ▼        ▼        ▼        ▼        ▼
       ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
       │  A  │ │  B  │ │  C  │ │  D  │ │  E  │ │  F  │ │  G  │ │  H  │
       │ S3  │ │ EC2 │ │ Fgt │ │ IAM │ │ Bed │ │ CT  │ │Creds│ │Obs  │
       │ M-L │ │  M  │ │  M  │ │  L  │ │ XL  │ │  S  │ │  M  │ │  M  │
       │ ~3d │ │ ~2d │ │~2.5d│ │ ~3d │ │ ~4d │ │~1.5d│ │~2.5d│ │ ~3d │
       └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
          │       │       │       │       │       │       │       │
          └───────┴───────┴───────┴───┬───┴───────┴───────┴───────┘
                                      │ INTEGRATION
                                      ▼
                          ┌─────────────────────────┐
                          │  Integration PR         │
                          │  All 8 slices merged    │
                          │  Opus review + final QA │
                          │  → dev                  │
                          └─────────────────────────┘
```

**Critical path is Foundation → max(A, B, C, D, E, F, G, H).** With parallel execution this is **~5 calendar days** for one Sonnet-on-eight-branches-with-an-Opus-coordinator workflow. Sequential, it would be ~22 days.

Slice H **prefers** A and F to be ~24 h from merging before it starts (it consumes their `S3__AWS__Client` and `CloudTrail__AWS__Client` implementations). It *can* run in parallel against the Foundation-shipped interface stubs and swap to the real clients during a final rebase.

Every other slice is fully independent of every other slice.

---

## 2. Why these boundaries

Each sibling pack owns:

- **One folder under `sgraph_ai_service_playwright__cli/aws/<surface>/`** (no other slice touches it)
- **One set of per-surface schema/enum/primitive/collection files** (additive — every new file is in its own file, no merge conflicts)
- **One `<Surface>__AWS__Client.py` implementation** (Foundation shipped the interface stub; slice fills in the body)
- **One per-namespace mutation-gate env var** (Foundation owns the decorator; each slice passes its env-var string)
- **Its own subset of the CLI verb tree** — Foundation locked the top-level `add_typer` registration in `Cli__Aws.py`, so slices only add verbs to their own `Cli__<Surface>.py` skeleton
- **One new user-guide page under `library/docs/cli/sg-aws/`**
- **Its own reality-doc update** under `team/roles/librarian/reality/aws-and-infrastructure/`

Files no sibling slice edits:

- `Cli__Aws.py` (top-level — Foundation only)
- `aws/_shared/*` (Foundation only; sibling slices import, never modify)
- Any other surface's folder

The **only file edited by more than one slice** (rare collisions, append-only):

- `library/docs/cli/sg-aws/README.md` — each slice adds one row to the "at-a-glance command map" table. Append-only; trivial rebase.

---

## 3. Per-slice size and dependencies

| Slice | Sibling pack | Size | Prod lines | Test lines | Critical deps | Touches files outside its folder |
|-------|--------------|------|-----------:|-----------:|---------------|----------------------------------|
| **0 Foundation** | (in umbrella) | S | ~1500 | ~600 | none | many — but **first**, so no conflicts |
| **A S3** | `v0.2.29__sg-aws-s3/` | M-L | ~2200 | ~800 | Foundation; `osbot-aws` S3 wrappers | `library/docs/cli/sg-aws/README.md` (1 row); new `09__s3.md` |
| **B EC2** | `v0.2.29__sg-aws-ec2/` | M | ~1400 | ~600 | Foundation; existing `scripts/provision_ec2.py`; existing `Elastic__AWS__Client` | same; new `10__ec2.md`; refactors `scripts/provision_ec2.py` to call new primitives |
| **C Fargate** | `v0.2.29__sg-aws-fargate/` | M | ~1500 | ~600 | Foundation; `osbot-aws` ECS wrappers | same; new `11__fargate.md` |
| **D IAM graph** | `v0.2.29__sg-aws-iam-graph/` | L | ~1800 | ~700 | Foundation; existing `aws/iam/` package | same; new `12__iam-graph.md`; extends existing `06__iam.md` |
| **E Bedrock** | `v0.2.29__sg-aws-bedrock/` | XL | ~2800 | ~900 | Foundation; `boto3-bedrock-runtime` / AgentCore SDK; vault store | same; new `13__bedrock.md` |
| **F CloudTrail** | `v0.2.29__sg-aws-cloudtrail/` | S | ~700 | ~400 | Foundation; `osbot-aws` CloudTrail wrappers | same; new `14__cloudtrail.md` |
| **G Scoped creds** | `v0.2.29__sg-aws-scoped-creds/` | M | ~1300 | ~600 | Foundation; existing `credentials/` package; vault store | same; new `15__creds.md` |
| **H Observability v1** | `v0.2.29__sg-aws-observability/` | M | ~1600 | ~700 | Foundation; **Slice A's `S3__AWS__Client`**; **Slice F's `CloudTrail__AWS__Client`**; existing `aws/logs/` (CloudWatch) | same; new `16__observe.md` |

**Total: ~14.8 K prod lines + ~5.9 K test lines.** Sequential ≈ 22 days. Parallel ≈ 5 days.

---

## 4. The parallelism rules

**Slices A, B, C, D, E, F, G can fire the moment Foundation merges.** They share no code at the implementation level.

**Slice H should fire when A and F are within ~24 h of merging.** It builds against the Foundation interface stubs in the meantime; the final ~30 min before its own PR is a rebase to pick up the real clients.

**No slice merges directly to `dev`.** All slices merge into the integration branch `claude/aws-primitives-support-uNnZY`. The integration branch merges to `dev` once all eight slices pass review and the Opus coordinator runs the full integration acceptance.

---

## 5. Per-slice prompt templates

Each Sonnet sub-agent receives:

1. A pointer to its sibling pack (`library/dev_packs/v0.2.29__sg-aws-<area>/README.md`)
2. A pointer to its source brief (`team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/...`)
3. A pointer to the umbrella `02__common-foundation.md` (the API contract it builds against)
4. The locked decisions in the umbrella `README.md`
5. A self-contained acceptance command sequence (lives in the sibling pack's `README.md`)

Skeleton prompt:

```
Role: Dev (Sonnet) working on the SG Playwright Service.

Task: implement Slice <X> of the v0.2.29 sg aws primitives expansion,
per the brief at library/dev_packs/v0.2.29__sg-aws-<area>/README.md.

Read in order:
  1. /.claude/CLAUDE.md
  2. library/dev_packs/v0.2.29__sg-aws-primitives-expansion/README.md
  3. library/dev_packs/v0.2.29__sg-aws-primitives-expansion/01__scope-and-architecture.md
  4. library/dev_packs/v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md  (your API contract)
  5. library/dev_packs/v0.2.29__sg-aws-<your area>/README.md  (+ any supporting files in the same folder)
  6. team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/<your source brief>.md
  7. library/guides/v3.63.4__type_safe.md
  8. library/guides/v3.1.1__testing_guidance.md

Constraints (non-negotiable):
  - Type_Safe everywhere, no Pydantic, no Literals
  - One class per file, empty __init__.py, no re-exports
  - No mocks, no patches — in-memory composition only
  - All AWS calls go through osbot-aws or existing aws/<svc>/service/*__AWS__Client
    classes wrapping Sg__Aws__Session — no direct boto3
  - 80-char ═══ headers in Python; YAML frontmatter in Markdown
  - Honour the Foundation API exactly (don't change signatures in aws/_shared/)
  - No work outside your slice's surface folder + your user-guide page +
    your reality-doc entry + your one row in library/docs/cli/sg-aws/README.md

When done:
  1. Run the acceptance sequence in your sibling pack's README
  2. Update the user-guide page (library/docs/cli/sg-aws/<NN>__<surface>.md) — required deliverable
  3. Update the reality-doc entry under team/roles/librarian/reality/aws-and-infrastructure/
  4. Commit with the message template in the brief
  5. Push to claude/aws-primitives-support-uNnZY-<slice-suffix>
  6. Open a PR against claude/aws-primitives-support-uNnZY
  7. Hand off — do NOT merge yourself
```

---

## 6. Coordination protocol

Three real coordination touch-points (down from v0.2.28's five — the sibling-pack structure removes most coordination):

### 6.1 The umbrella `README.md` — read-only after sign-off

All sibling packs read it. None edit it. If a sibling needs to amend a locked decision, the answer is "raise an Architect-review request and update the umbrella separately" — not "edit the umbrella in your PR."

### 6.2 `library/docs/cli/sg-aws/README.md` "at-a-glance command map" — append-only

Each slice adds one branch row to the tree. Trivial rebase if two land at the same time.

### 6.3 The Foundation interface stubs in `aws/_shared/`

If a sibling slice needs a signature change in `_shared/`, it must coordinate with the umbrella and any other affected slices. Default rule: **don't change signatures**. If you genuinely need to (rare), open an Architect-review request and the Opus coordinator amends Foundation in a hotfix PR before the affected slice resumes.

---

## 7. Acceptance gates between phases

After each PR merges into the integration branch, the Opus coordinator runs the full acceptance:

| Gate | Trigger | Commands |
|------|---------|----------|
| **G0** | Foundation PR | acceptance section of `02__common-foundation.md` |
| **G-A** | Slice A merges | acceptance section of `v0.2.29__sg-aws-s3/README.md` |
| **G-B** | Slice B merges | acceptance section of `v0.2.29__sg-aws-ec2/README.md` |
| **G-C** | Slice C merges | acceptance section of `v0.2.29__sg-aws-fargate/README.md` |
| **G-D** | Slice D merges | acceptance section of `v0.2.29__sg-aws-iam-graph/README.md` |
| **G-E** | Slice E merges | acceptance section of `v0.2.29__sg-aws-bedrock/README.md` |
| **G-F** | Slice F merges | acceptance section of `v0.2.29__sg-aws-cloudtrail/README.md` |
| **G-G** | Slice G merges | acceptance section of `v0.2.29__sg-aws-scoped-creds/README.md` |
| **G-H** | Slice H merges | acceptance section of `v0.2.29__sg-aws-observability/README.md` |
| **G-Final** | All merged into integration | Cross-surface integration: `agent-trace` in observability REPL pulls a real session that touches S3 + CloudWatch + CloudTrail; one full end-to-end from `sg aws ec2 create` → tagged → discovered by `sg aws observe`; `sg aws creds get --scope iam:read-only` succeeds and the assumption is visible in `cloudtrail events list` |

A failed gate **blocks the integration→dev merge**, not the next slice's PR. Slices continue in parallel; integration is the choke point.

---

## 8. Risk register (orchestration-specific)

| Risk | Mitigation |
|------|-----------|
| Two slices collide on the at-a-glance command map | Append-only; rebase trivial |
| Slice H blocked because A or F late | Foundation ships interface stubs; H builds against them; final rebase swaps to real clients |
| Foundation PR slips and blocks all 8 | Foundation is intentionally small (~1500 prod lines); reviewable in one pass; no verb bodies |
| A slice invents a direct boto3 call to "save time" | Code review enforces CLAUDE.md rule #14; Foundation makes the `Sg__Aws__Session` path the easy path |
| Slice E (Bedrock) discovers AgentCore SDK gaps mid-flight | Bedrock README explicitly carves out chat (boto3-bedrock-runtime, low risk) from agent/tool (AgentCore SDK, higher risk); if AgentCore blocks, chat ships standalone and agent/tool defer to v0.2.30 |
| Slice G (creds) ships an authorisation gap | AppSec review before merge; the scope catalogue starts with read-only scopes only |
| Cancelling a slice mid-flight | Sibling-pack structure makes this clean: archive the sibling pack with `STATUS: CANCELLED`, drop the row from the umbrella sibling-pack index, no other artefact needs changing |

---

## 9. Quick-reference orchestration commands

For the Opus coordinator running this milestone:

```bash
# Step 1 — fire Foundation
#   (subagent: Sonnet, prompt: agent-0 template, branch: …-foundation)

# Step 2 — once Foundation merged, fire A/B/C/D/E/F/G in parallel
#   (7× subagent: Sonnet, prompts: per-slice templates above,
#    branches: …-{s3,ec2,fargate,iam-graph,bedrock,cloudtrail,creds})

# Step 3 — fire H when A+F are ~24h from merging (or in parallel against stubs)
#   (subagent: Sonnet, prompt: agent-H template, branch: …-observability)

# Step 4 — run G-Final acceptance against integration branch
pytest tests/integration/sgraph_ai_service_playwright__cli/aws/test_integration_v0_2_29.py -v

# Step 5 — open PR integration → dev
```

---

## 10. What "done" looks like

When this milestone closes (v0.2.29 release):

- `sg aws --help` shows: `acm | billing | cf | cloudtrail | creds | credentials | dns | ec2 | fargate | iam | lambda | logs | observe | s3 | bedrock`
- `sg aws iam --help` shows the new `graph` sub-group
- All eight acceptance sequences from the sibling packs pass green
- The G-Final cross-surface integration suite passes green
- `library/docs/cli/sg-aws/` has 16 user-guide pages (1 README + `01..16__*.md`)
- The reality doc at `team/roles/librarian/reality/aws-and-infrastructure/` lists all eight new surfaces as `LANDED — v0.2.29`
- A debrief at `team/claude/debriefs/v0.2.29__sg-aws-primitives-expansion.md` lists the good-failures and bad-failures from each slice (one bullet per slice minimum)
- The follow-up v0.2.30 packs are scaffolded: vault-aware-S3, container-hosts, instance-sizing, Bedrock-kb/guardrail/eval, IAM-graph-phase-4, scoped-creds-Phase-5-deployment, observability-product-analytics
