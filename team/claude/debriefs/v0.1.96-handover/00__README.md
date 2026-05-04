# v0.1.96 Stack-Split Refactor — Session Handover Pack

**Created:** 2026-04-26
**Branch:** `claude/refactor-playwright-image-FVPDf`
**Commits since `dev` divergence:** 28
**State:** Phase A complete · Phase B `sp os` complete · Phase B `sp prom` foundation (6a) done · 7 more `sp prom` slices + `sp vnc` + Phase C + Phase D remaining

---

## Purpose

This pack is a **session-handover dev-pack**. Read it top-to-bottom and you have everything needed to continue the v0.1.96 playwright-stack-split refactor without re-discovering context.

The previous session built a lot, established patterns, and surfaced multiple gotchas. The original 8-doc plan is approved and signed off; the proven sister-section template (`sp os`) is fully shipped end-to-end. What remains is mechanical application of the same template plus the strip + cleanup phases.

## Reading order

| File | Purpose | Lines |
|---|---|---|
| `00__README.md` | This file — pack overview + resumption prompt at the bottom | ~60 |
| `01__original-task.md` | What the operator asked for; pointer to the 8 plan docs | ~70 |
| `02__what-shipped.md` | Concrete state per phase + commit hashes | ~80 |
| `03__patterns-and-conventions.md` | Small-file discipline, `_Fake_*` test pattern, sister-section composition | ~80 |
| `04__lessons-learned.md` | Bugs caught + invariants locked by tests | ~80 |
| `05__key-commits.md` | Annotated commit list — read these to understand the shape | ~70 |
| `06__sister-section-template.md` | The proven 9-slice shape from `sp os` (5a→5i) for `sp prom` and `sp vnc` to follow | ~90 |
| `07__remaining-phases.md` | What's left: Phase B step 6b–6h, B7 `sp vnc`, Phase C strip, Phase D cleanup | ~100 |
| `08__resumption-prompt.md` | The exact prompt to copy-paste to the next agent | ~50 |

## Resumption prompt (TL;DR)

> Continuing the v0.1.96 playwright stack split refactor on branch `claude/refactor-playwright-image-FVPDf`. Read `team/claude/debriefs/v0.1.96-handover/` in order (00 → 08), then continue at **Phase B step 6b** — `sp prom` schemas + collections. Follow the proven `sp os` template; keep small-file / single-responsibility discipline. No `unittest.mock`, only real `_Fake_*` subclasses.

Full prompt with environment setup is in `08__resumption-prompt.md`.

## Trust model

- All 28 commits pushed to `origin/claude/refactor-playwright-image-FVPDf`
- All 21 sub-slices have their own dated debrief in `team/claude/debriefs/`, indexed in `team/claude/debriefs/index.md`
- Reality doc updated in the same commit as code (`team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md`)
- 251 tests in my work areas, all green; 1 unchanged pre-existing failure unrelated to this work

If anything in this pack contradicts the actual code or a debrief, **trust the code + debrief**. This pack is a summary; debriefs are the source.
