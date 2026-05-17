---
title: "03 — Sonnet sub-agent orchestration plan"
file: 03__sonnet-orchestration-plan.md
author: Architect (Claude)
date: 2026-05-17 (rev 2)
parent: README.md
---

# 03 — Sonnet sub-agent orchestration plan

How to ship this milestone. Rev 2 accommodates **v2-first sequencing** (decided 2026-05-17, v0.2.23 plan Q1): v2 vault-publish ships its phases 2a (`sg aws cf` expansion) and 2b (`sg aws lambda` expansion) first; the lab harness composes against those once they're in.

This is the centrepiece of the pack. The per-agent briefs (`04`-`08`) are the self-contained handoffs a Sonnet agent receives.

---

## 1. The shape (rev 2)

```
                  ┌──────────────────────────────────────┐
                  │   Agent 0 — Foundation               │
                  │   ~1 day, Sonnet, Opus-reviewed      │
                  │   File: 02__common-foundation.md     │
                  │   PR → claude/aws-primitives-…       │
                  └────────────────┬─────────────────────┘
                                   │ MERGED FIRST
                                   ▼
                  ┌────────────────┴─────────────────────┐
                  ▼                                      ▼
       ┌────────────────┐                     ┌────────────────────┐
       │   Agent A      │                     │     Agent E        │
       │   DNS exps     │                     │   Viewer + diff    │
       │   (P0+P1)      │                     │     (P5)           │
       │   ~2 days, S   │                     │   ~1 day, S        │
       │                │                     │                    │
       │  No v2 dep —   │                     │  Fully independent │
       │  fire now      │                     │  Fire now          │
       └───────┬────────┘                     └─────────┬──────────┘
               │                                        │
               │   ┌──────────────────────────────┐     │
               │   │ v2 vault-publish phases 2a + │     │
               │   │ 2b ship `sg aws cf` and `sg  │     │
               │   │ aws lambda` expansions       │     │
               │   │  ← GATING DEPENDENCY ←       │     │
               │   └────────┬─────────┬───────────┘     │
               │            │         │                 │
               ▼            ▼         ▼                 │
       ┌────────────────┐ ┌──────────────────┐          │
       │   Agent B      │ │    Agent C       │          │
       │   Lambda exps  │ │    CF exps       │          │
       │   (P2)         │ │    (P3)          │          │
       │   ~1.5d, M     │ │    ~2 d, M       │          │
       │ ← needs v2 2b  │ │ ← needs v2 2a    │          │
       └───────┬────────┘ └─────────┬────────┘          │
               │                    │                   │
               └─────────┬──────────┘                   │
                         ▼                              │
                ┌────────────────┐                      │
                │   Agent D      │                      │
                │   Transition   │                      │
                │   (P4)         │                      │
                │   ~1.5d, M     │                      │
                │ ← needs A+B+C  │                      │
                └────────┬───────┘                      │
                         │                              │
                         └──────────┬───────────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │  Integration PR         │
                       │  All slices merged      │
                       │  Opus review + final QA │
                       │  → dev                  │
                       └─────────────────────────┘
```

**Critical path = Foundation → max(A, max(v2 2b, v2 2a) → max(B, C) → D, E).**

- **Foundation + A + E** are unblocked the moment Foundation merges. With one Sonnet at a time: ~3 calendar days. With two parallel Sonnets: ~2 days.
- **B and C** are gated on v2 phases 2b and 2a respectively. Once those land, B and C fire in parallel and finish in ~2 days.
- **D** lands last, ~1.5 days.

Sequential worst case: ~7 days of Sonnet work + the v2 wait. Best case with parallelism: ~4 days of Sonnet work + the v2 wait.

---

## 2. Why these boundaries

Each agent owns:

- **One sub-folder under `experiments/`** (no other agent touches it)
- **One set of per-experiment result schemas** (additive — every new schema file is in its own file, no merge conflicts)
- **One `Lab__Teardown__*.py` implementation** (Agent A owns R53; B owns Lambda+IAM; C owns CF+ACM+SG; D owns nothing new; E owns nothing)
- **Its own registry entries** (each agent appends ~5 lines to `registry.py` — the only file shared across agents)
- **Its own subset of the CLI sub-verb tree** (e.g. `sg aws lab dns *`, `sg aws lab lambda *`) — but the top-level shape is locked by the foundation so agents only add sub-verbs

The only file all five agents touch is `service/experiments/registry.py`. Conflicts there are append-only and trivial.

**No agent touches `sg aws cf` or `sg aws lambda` packages.** Those expansions belong to v2 vault-publish phases 2a/2b per decision #2. If an agent finds they need a verb that doesn't exist there yet, the answer is "wait for v2" — not "add it here".

---

## 3. Per-agent size and dependencies

| Agent | Size | Lines of prod | Lines of test | Critical deps | Touches files outside its folder |
|-------|------|--------------:|--------------:|---------------|----------------------------------|
| **0 Foundation** | S | ~1500 | ~600 | none | many — but **first**, so no conflicts |
| **A DNS** | S | ~900 | ~500 | Foundation; existing `Route53__AWS__Client` | `registry.py` (5 lines); `Render__Timeline__ASCII` |
| **B Lambda** | M | ~1200 | ~500 | Foundation; **v2 phase 2b (`sg aws lambda` expansion)**; existing `Lambda__AWS__Client`; `osbot-aws.Deploy_Lambda` | `registry.py` (6 lines); `Render__Histogram__ASCII` |
| **C CloudFront** | M | ~1200 | ~400 | Foundation; **v2 phase 2a (`sg aws cf` expansion)**; existing `CloudFront__AWS__Client` | `registry.py` (5 lines) |
| **D Transition** | M | ~1100 | ~400 | Foundation + A + B + C | `registry.py` (4 lines); enriched `Render__Timeline__ASCII` |
| **E Viewer** | S | ~700 | ~300 | Foundation | `Render__HTML`, `runs diff` impl |

Total: **~6600 production lines + ~2700 test lines** across 6 PRs (down from rev 1's 8400+3100, after dropping the primitive expansions and temp clients).

---

## 4. The parallelism rules

**Agents A and E can fire the moment Foundation merges.** They share no code at the implementation level.

**Agents B and C cannot start until v2 phases 2b and 2a (respectively) merge into `dev`.** They have no temp-client fallback (per decision #2).

**Agent D fires when A + B + C have all merged into the integration branch.**

**No agent merges directly to `dev`.** All agents merge into the integration branch `claude/aws-primitives-support-NVyEh`. The integration branch merges to `dev` once all slices pass review and the Opus coordinator runs the full integration acceptance.

---

## 5. Per-agent prompt templates

Each Sonnet sub-agent gets:

1. A pointer to its per-agent brief (`library/dev_packs/v0.3.0__sg-aws-lab-harness/0X__agent-N__….md`)
2. A pointer to the source brief (`team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/`)
3. A pointer to **the deltas doc** (`team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md`) — sections B.1-B.7 are non-negotiable corrections
4. A pointer to `02__common-foundation.md`
5. The locked decisions in `README.md`
6. A self-contained acceptance command sequence (lives in the per-agent brief)

Skeleton prompt:

```
Role: Dev (Sonnet) working on the SG Playwright Service.

Task: implement Slice <N> of the v0.3.0 sg aws lab milestone, per the
brief at library/dev_packs/v0.3.0__sg-aws-lab-harness/<NN>__agent-<X>__….md.

Read in order:
  1. /.claude/CLAUDE.md
  2. library/dev_packs/v0.3.0__sg-aws-lab-harness/README.md
  3. library/dev_packs/v0.3.0__sg-aws-lab-harness/01__scope-and-architecture.md
  4. library/dev_packs/v0.3.0__sg-aws-lab-harness/02__common-foundation.md
  5. library/dev_packs/v0.3.0__sg-aws-lab-harness/<your slice>.md
  6. team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/<your category>.md
  7. team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md
     ↑ READ §B.1 THROUGH §B.7 — non-negotiable lab-brief corrections.
  8. library/guides/v3.63.4__type_safe.md
  9. library/guides/v3.1.1__testing_guidance.md

Constraints (non-negotiable):
  - Type_Safe everywhere, no Pydantic, no Literals
  - One class per file, empty __init__.py, no re-exports
  - File names MATCH class names exactly — no E01__ numeric prefix
    (per delta B.3)
  - No raw collection types (Set__Str, Dict__Str__Str, Dict__Str__Int) —
    use Type_Safe__Dict__Safe_Str__Safe_Str etc. (per delta B.1, B.4)
  - Lab__Experiment.execute() takes no runner argument; runner is injected
    as a field at setup() time (per delta B.2)
  - No mocks, no patches — in-memory composition only
  - All AWS calls route through Sg__Aws__Session.from_context().boto3_client_from_context()
    via the existing aws/<svc>/service/*__AWS__Client classes — NO bare boto3,
    NO temp boto3 wrappers (per decision #2 and #6)
  - 80-char ═══ headers in Python; YAML frontmatter in Markdown
  - No work outside your slice's experiments/<category>/ folder + your
    Lab__Teardown__<type>.py + your registry entries

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

Agent A writes the baseline `Render__Timeline__ASCII`. Agent D extends it (for the composite waterfall view). Agent B writes the baseline `Render__Histogram__ASCII` (for cold-start distributions).

To avoid conflicts:

- Foundation ships **stub** `Render__Timeline__ASCII.py` and `Render__Histogram__ASCII.py` with the public API signed (method signatures), but bodies raising `NotImplementedError`.
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
| **G-A** | Agent A merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run propagation-timeline --ttl 60` + `sg aws lab sweep` shows empty |
| **G-B** | Agent B merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run lambda-cold-start --repeat 5` |
| **G-C** | Agent C merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run cf-distribution-inspect <existing-dist-id>` (Tier-0); + one Tier-2 like `cf-cache-policy-enforcement` |
| **G-D** | Agent D merges | `SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run dns-swap-window`; once A+B+C in: `full-cold-path-end-to-end --tier-2-confirm` |
| **G-E** | Agent E merges | `sg aws lab serve --port 8090` opens; `sg aws lab runs diff <A> <B>` produces a diff |
| **G-Final** | All merged into integration | Kill-9 acceptance test (`lab-brief §4.8`) passes for all categories; sweeper finds nothing post-test |

A failed gate **blocks the integration→dev merge**, not the next agent's PR.

---

## 8. Risk register (orchestration-specific, rev 2)

| Risk | Mitigation |
|------|-----------|
| Two agents collide on `registry.py` | Append-only file, rebase resolves; Opus coordinator polices |
| Foundation PR slips and blocks A + E | Foundation is intentionally small (~1500 prod lines); has its own acceptance; reviewable in one pass |
| **v2 phase 2a or 2b slips and blocks B or C** | A and E ship anyway. Reality-doc and changelog mark B/C as "pending v2". This is a deliberate trade — we don't carry temp boto3 wrappers (decision #2). |
| An agent invents a "tiny boto3 wrapper" | CLAUDE.md rule #14 + decision #6 review check; reject in code review. Foundation has zero boto3 imports outside `Sg__Aws__Session`. |
| An agent's slice provisions a CF distribution that costs money during dev iteration | Tier-2 experiments gated by `--tier-2-confirm` AND `SG_AWS__LAB__ALLOW_MUTATIONS=1`; dev iteration uses `--dry-run` |
| Lambda agent's in-tree lab Lambdas accidentally deploy globally | Hard `timeout=30` + `reserved_concurrency=2` on every lab Lambda (set via the v2-expanded `sg aws lambda <name> concurrency set`); `Lab__Tagger` applies the lab tag set |
| Agent E's HTML viewer leaks `.sg-lab/runs/` over the network | `serve` binds to `127.0.0.1` only; explicit `--host 0.0.0.0` flag required with confirmation; documented in CLI help |
| **An agent replicates a lab-brief CLAUDE.md violation** (raw `Dict__Str__Str`, `E01__` filename, runner-per-call) | Per-agent prompt template (step 7) reads `03__delta-from-lab-brief.md` B.1-B.7 before writing any code |

---

## 9. Quick-reference orchestration commands

For the Opus coordinator running this milestone:

```bash
# Step 1 — fire Foundation
#   (subagent: Sonnet, prompt: agent-0-foundation template, branch: …-foundation)

# Step 2 — once Foundation merged, fire A and E in parallel
#   (2× subagent: Sonnet, prompts: agent-A/E templates, branches: …-{dns,viewer})

# Step 3 — wait for v2 vault-publish phase 2a (sg aws cf) to merge to dev.
#          Fire Agent C.
#   (subagent: Sonnet, prompt: agent-C template, branch: …-cf)

# Step 4 — wait for v2 vault-publish phase 2b (sg aws lambda) to merge to dev.
#          Fire Agent B.
#   (subagent: Sonnet, prompt: agent-B template, branch: …-lambda)

# Step 5 — once B+C merge into integration, fire D
#   (subagent: Sonnet, prompt: agent-D template, branch: …-transition)

# Step 6 — run G-Final acceptance against integration branch
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety.py

# Step 7 — open PR integration → dev
```

---

## 10. What "done" looks like

When the milestone closes:

- `sg aws lab list` shows ~24 experiments
- All experiments work
- `sg aws lab sweep` after any sequence of runs returns "no leaked resources"
- The full kill-9 safety test passes for every resource type
- The v2 brief's Q1 and Q2 are answered with empirical numbers (Q3/Q4/Q5 too, once B+C+D land)
- The Architect debrief at `team/claude/debriefs/v0.3.0__sg-aws-lab.md` lists the good-failures and bad-failures from each agent's slice
- Reality doc `team/roles/librarian/reality/cli/index.md` lists `sg aws lab` as ✅ EXISTS
- Catalogue shard `library/catalogue/cli.md` lists `sg aws lab` with its verbs
