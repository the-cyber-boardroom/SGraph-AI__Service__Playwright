---
title: "03 — Sonnet sub-agent orchestration plan"
file: 03__sonnet-orchestration-plan.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 03 — Sonnet sub-agent orchestration plan

How to ship this milestone with **one foundation PR followed by 5 parallel Sonnet sub-agents**, each independent enough to land its slice without coordinating with the others mid-flight.

This is the centrepiece of the pack. The per-agent briefs (`04`-`08`) are the self-contained handoffs a Sonnet agent receives.

---

## 1. The shape

```
                  ┌──────────────────────────────────────┐
                  │   Agent 0 — Foundation               │
                  │   ~1 day, Sonnet, Opus-reviewed      │
                  │   File: 02__common-foundation.md     │
                  │   PR → claude/aws-primitives-…       │
                  └────────────────┬─────────────────────┘
                                   │ MERGED FIRST
                                   ▼
              ┌──────────────┬──────────────┬──────────────┬──────────────┐
              ▼              ▼              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
       │  Agent A   │ │  Agent B   │ │  Agent C   │ │  Agent D   │ │  Agent E   │
       │  DNS exps  │ │ Lambda exps│ │   CF exps  │ │ Transition │ │  Viewer +  │
       │   (P0+P1)  │ │   + prim   │ │   + prim   │ │   (P4)     │ │   diff(P5) │
       │            │ │   expand   │ │   expand   │ │            │ │            │
       │  ~2 days   │ │  ~2.5 days │ │  ~2.5 days │ │  ~1.5 days │ │  ~1 day    │
       │  S size    │ │  L size    │ │  L size    │ │  M size    │ │  S size    │
       │  File: 04  │ │  File: 05  │ │  File: 06  │ │  File: 07  │ │  File: 08  │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │              │              │              │              │
             └──────────────┴──────────┬───┴──────────────┴──────────────┘
                                       │ INTEGRATION
                                       ▼
                          ┌─────────────────────────┐
                          │  Integration PR         │
                          │  All 5 slices merged    │
                          │  Opus review + final QA │
                          │  → dev                  │
                          └─────────────────────────┘
```

**Critical path is Foundation → max(A, B, C, D, E).** With parallel execution this is ~3.5 calendar days for one Sonnet-on-five-branches-with-an-Opus-coordinator workflow. Sequential, it would be ~10 days.

Agent D **prefers** A+B+C to be merged before it starts (E27 is the full e2e composite). It *can* run in parallel using the temp clients, but the cleanest sequencing is to let A/B/C settle into the integration branch and pick those up.

Agent E is fully independent of A/B/C/D and can land any time after the foundation.

---

## 2. Why these boundaries

Each agent owns:

- **One sub-folder under `experiments/`** (no other agent touches it)
- **One set of per-experiment result schemas** (additive — every new schema file is in its own file, no merge conflicts)
- **One `Lab__Teardown__*.py` implementation** (Agent A owns R53; B owns Lambda+IAM; C owns CF+ACM+SG; D owns nothing new; E owns nothing)
- **Its own registry entries** (each agent appends ~5 lines to `registry.py` — the only file shared across agents)
- **Its own subset of the CLI sub-verb tree** (e.g. `sg aws lab dns *`, `sg aws lab lambda *`) — but the top-level shape is locked by the foundation so agents only add sub-verbs

The only file all five agents touch is `service/experiments/registry.py`. Merge conflicts there are append-only and trivial.

---

## 3. Per-agent size and dependencies

| Agent | Size | Lines of prod | Lines of test | Critical deps | Touches files outside its folder |
|-------|------|--------------:|--------------:|---------------|----------------------------------|
| **0 Foundation** | S | ~1500 | ~600 | none | many — but **first**, so no conflicts |
| **A DNS** | S | ~900 | ~500 | Foundation; existing `Route53__AWS__Client` | `registry.py` (5 lines); Render__Timeline__ASCII |
| **B Lambda** | L | ~2200 | ~700 | Foundation; `osbot-aws.Deploy_Lambda`; existing `Lambda__AWS__Client` | `registry.py` (6 lines); `aws/lambda_/cli/` (new verbs); `Render__Histogram__ASCII` |
| **C CloudFront** | L | ~2000 | ~600 | Foundation; existing `CloudFront__AWS__Client` | `registry.py` (5 lines); `aws/cf/cli/` (new verbs) |
| **D Transition** | M | ~1100 | ~400 | Foundation + A + B + C (uses everything) | `registry.py` (4 lines); enriched `Render__Timeline__ASCII` |
| **E Viewer** | S | ~700 | ~300 | Foundation | `Render__HTML`, `Render__Timeline__ASCII`, `Render__Histogram__ASCII`, `runs diff` impl |

Total: **~8400 production lines + ~3100 test lines** across 6 PRs.

---

## 4. The parallelism rules

**Agents A, B, C, E can fire the moment Foundation merges.** They share no code at the implementation level.

**Agent D should fire when A, B, C are within ~24 h of merging.** It needs the working clients (or the temp clients) to write E27. It can write E40/E41/E42 in parallel using just A's R53 work.

**No agent merges directly to `dev`.** All agents merge into the integration branch `claude/aws-primitives-support-NVyEh`. The integration branch merges to `dev` once all five slices pass review and the Opus coordinator runs the full integration acceptance.

---

## 5. Per-agent prompt templates

Each Sonnet sub-agent gets:

1. A pointer to its per-agent brief (`library/dev_packs/v0.2.28__sg-aws-lab-harness/0X__agent-N__….md`)
2. A pointer to the source brief (`team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/`)
3. A pointer to `02__common-foundation.md`
4. The locked decisions in `README.md`
5. A self-contained acceptance command sequence (lives in the per-agent brief)

Skeleton prompt:

```
Role: Dev (Sonnet) working on the SG Playwright Service.

Task: implement Slice <N> of the v0.2.28 sg aws lab milestone, per the
brief at library/dev_packs/v0.2.28__sg-aws-lab-harness/<NN>__agent-<X>__….md.

Read in order:
  1. /.claude/CLAUDE.md
  2. library/dev_packs/v0.2.28__sg-aws-lab-harness/README.md
  3. library/dev_packs/v0.2.28__sg-aws-lab-harness/01__scope-and-architecture.md
  4. library/dev_packs/v0.2.28__sg-aws-lab-harness/02__common-foundation.md
  5. library/dev_packs/v0.2.28__sg-aws-lab-harness/<your slice>.md
  6. team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/<your category>.md
  7. library/guides/v3.63.4__type_safe.md
  8. library/guides/v3.1.1__testing_guidance.md

Constraints (non-negotiable):
  - Type_Safe everywhere, no Pydantic, no Literals
  - One class per file, empty __init__.py, no re-exports
  - No mocks, no patches — in-memory composition only
  - All AWS calls go through osbot-aws or existing aws/<svc>/service/*__AWS__Client
    classes — the documented temp-client exception is the only allowed boto3
  - 80-char ═══ headers in Python; YAML frontmatter in Markdown
  - No work outside your slice's experiments/<category>/ folder + your
    Lab__Teardown__<type>.py + your registry entries + your per-agent CLI subverbs

When done:
  1. Run the acceptance sequence in your brief
  2. Commit with the message template in the brief
  3. Push to claude/aws-primitives-support-NVyEh-<slice-suffix>
  4. Open a PR against claude/aws-primitives-support-NVyEh
  5. Hand off — do NOT merge yourself
```

---

## 6. Coordination protocol

Two real coordination touch-points:

### 6.1 Registry conflicts (append-only, trivial)

The only shared file. Each agent appends entries to a single dict. The Opus coordinator handles the (rare) conflict — typically `git rebase --autosquash` handles it.

### 6.2 The `Render__Timeline__ASCII` and `Render__Histogram__ASCII` files

Agent A writes the baseline `Render__Timeline__ASCII`. Agent D extends it (for E27's waterfall view). Agent B writes the baseline `Render__Histogram__ASCII` (for cold-start distributions).

To avoid conflicts:

- Foundation ships **stub** `Render__Timeline__ASCII.py` and `Render__Histogram__ASCII.py` with the public API signed (method signatures + dataclass-style result-row schemas), but bodies raising `NotImplementedError`.
- Agent A fills in `Timeline.render_event_list(...)`.
- Agent B fills in `Histogram.render_durations_ms(...)`.
- Agent D adds `Timeline.render_waterfall(...)` (new method, not an edit of the existing one).
- Agent E adds the HTML renderers (separate file `Render__HTML.py`).

This keeps the three renderer files conflict-free across PRs.

---

## 7. Acceptance gates between phases

After each PR merges into the integration branch, the Opus coordinator runs the full acceptance:

| Gate | Trigger | Commands |
|------|---------|----------|
| **G0** | Foundation PR | `pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/` + `sg aws lab list / sweep / account show` |
| **G-A** | Agent A merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E11 --ttl 60` + `sg aws lab sweep` shows empty |
| **G-B** | Agent B merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E30 --repeat 5` + the new `sg aws lambda <name> alias create`/`permissions` verbs work |
| **G-C** | Agent C merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E20 <existing-dist-id>` + the new `sg aws cf distribution update/invalidate/tags` verbs work |
| **G-D** | Agent D merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E40` + (if A/B/C all in) `E27 --tier-2-confirm` |
| **G-E** | Agent E merges | `sg aws lab serve --port 8090` opens; `sg aws lab runs diff <A> <B>` produces a diff |
| **G-Final** | All merged into integration | Kill-9 acceptance test (`lab-brief §4.8`) passes for all 4 categories; sweeper finds nothing post-test |

A failed gate **blocks the integration→dev merge**, not the next agent's PR. Agents continue in parallel; integration is the choke point.

---

## 8. Risk register (orchestration-specific)

| Risk | Mitigation |
|------|-----------|
| Two agents collide on `registry.py` | Append-only file, rebase resolves; Opus coordinator polices |
| Agent D blocked because A/B/C late | D can start with E40/E41 (DNS-only); E42/E27 wait |
| Foundation PR slips and blocks all 5 | Foundation is intentionally small (~1500 prod lines); has its own acceptance; reviewable in one pass |
| An agent invents a "tiny boto3 wrapper" outside `temp_clients/` | CLAUDE.md rule #14 review check; reject in code review |
| An agent's slice provisions a CF distribution that costs money during dev iteration | Tier-2 experiments are gated by `--tier-2-confirm` AND `SG_AWS__LAB__ALLOW_MUTATIONS=1`; dev iteration uses `--dry-run` |
| Lambda agent's in-tree lab Lambdas accidentally deploy globally | Hard `timeout=30` + `reserved_concurrency=2` on every lab Lambda; `Lab__Tagger` applies the lab tag set |
| Agent E's HTML viewer leaks `.sg-lab/runs/` over the network | `serve` binds to `127.0.0.1` only; explicit `--host 0.0.0.0` flag required to expose externally; documented in CLI help |

---

## 9. Quick-reference orchestration commands

For the Opus coordinator running this milestone:

```bash
# Step 1 — fire Foundation
#   (subagent: Sonnet, prompt: agent-0-foundation template, branch: …-foundation)

# Step 2 — once Foundation merged, fire A/B/C/E in parallel
#   (4× subagent: Sonnet, prompts: agent-A/B/C/E templates, branches: …-{dns,lambda,cf,viewer})

# Step 3 — once A+B+C merge into integration, fire D
#   (subagent: Sonnet, prompt: agent-D template, branch: …-transition)

# Step 4 — run G-Final acceptance against integration branch
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety.py

# Step 5 — open PR integration → dev
```

---

## 10. What "done" looks like

When the milestone closes:

- `sg aws lab list` shows ~24 experiments
- `sg aws lab run E01 .. E42` all work
- `sg aws lab sweep` after any sequence of runs returns "no leaked resources"
- The full kill-9 safety test passes for every resource type
- `sg aws cf distribution update / invalidate / tags / origin-group / oac` exist and have tests
- `sg aws lambda <name> deploy-from-image / alias / permissions / concurrency / env` exist and have tests
- The v2 brief's Q1 and Q2 are answered with empirical numbers
- The Architect debrief at `team/claude/debriefs/v0.2.28__sg-aws-lab.md` lists the good-failures and bad-failures from each agent's slice
- Reality doc `team/roles/librarian/reality/v0.1.31/*aws*.md` is updated to include the new lab namespace and the expanded primitive verbs
