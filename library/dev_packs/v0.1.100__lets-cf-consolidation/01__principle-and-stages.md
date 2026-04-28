# 01 — Principle and Stages

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Restate the LETS principle from slice 1, then show how this slice extends it into **L-C-E-T-S** by inserting a **C (Consolidate)** stage. Argue *why* C is the missing persistent step — i.e. why E (Extract) becomes ephemeral-on-purpose once the consolidated artefact captures parsed-and-classified state.

This doc stays focused on CloudFront. The broader pattern (the same C-stage applied to mitm flows, Playwright sessions, audit logs) lives in `00b__consolidation-lets-pattern.md` and `09__lets-workflow-taxonomy.md`. Cross-reference, do not re-explain.

---

## Sections to include

When you (Sonnet) expand this stub, structure the doc as follows:

1. **The principle, restated** — pull the verbatim quote from slice 1's `01__principle-and-stages.md` and explain what it means for *this* slice.

2. **Today's L-E-T-S mapping** — what each letter does in the existing pipeline (slice 1 + slice 2). One sentence per letter is enough; full detail is in `00__cloudfront-lets-architecture-review.md`.

3. **The new L-C-E-T-S mapping** — what changes. Specifically:
   - L still means S3 ListObjectsV2 + inventory
   - C is new: persists the *parsed-and-classified* form
   - E becomes "the cheap function that re-runs on demand" — no longer the bottleneck
   - T and S unchanged

4. **Why the C stage honours the LETS principle better than the current pipeline does** — this is the conceptual heart of the doc. Today the pipeline persists L (Firehose drops) and S (ES indices) but treats E as ephemeral. Re-runs redo the parse work. The consolidated artefact captures that work. E is now allowed to be ephemeral *because* the consolidation persists its output.

5. **The compatibility-region innovation** — the `lets-config.json` at folder root (decision #5 in the README) is what makes the C-layer durable across schema evolution. A doc-level explanation of why this design choice falls out of the LETS principle: persisting the *toolchain assertion* alongside the *data* is what turns a cache into a real persistence layer.

6. **What this slice does NOT change** — slice 1 stays as-is, slice 2 gains a new queue mode (`--from-consolidated`) but its existing modes still work. Cross-reference §"What's NOT in this slice" in the README.

---

## Source material

When expanding this stub, draw from:

- The README of this brief (especially §"Why this brief exists" and decisions #2–#5)
- `00__cloudfront-lets-architecture-review.md` §3 ("The LETS principle")
- `00b__consolidation-lets-pattern.md` §5 ("Why this is more than an optimisation")
- Slice 1 brief: `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/01__principle-and-stages.md`

---

## Target length

~80–100 lines, matching slice 1's `01__principle-and-stages.md`. This doc is conceptual, not operational — keep it tight.
