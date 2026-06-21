---
title: "07 — Implementation plan & multi-agent orchestration"
file: 07__implementation-plan.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED — plan only, no code
parent: README.md
---

# 07 — Implementation plan & orchestration

How to ship this milestone: seven sequenced phases, fanned out across independent
agent slices in the style of the lab-harness `03__sonnet-orchestration-plan.md`.
Phase 1 is the cheap, high-confidence bug-fixes + `/health/capabilities` wiring;
everything after composes on that clean base.

---

## 1. Phase sequence

| Phase | Name | Depends on | Brief | Size |
|-------|------|-----------|-------|------|
| **P1** | Bug-fixes + capability bootstrap | — (fire first) | 00 §3, 01 §1/§5 | S |
| **P2** | Capability tabs (Sequence/Inspect/Session/Browser/Debug/Service) | P1 | 01 §3 | L |
| **P3** | Workflow import/export + gallery | P2 | 02, 03 | M |
| **P4** | In-app docs & help + verb-table drift test | P2 | 04, 06 §5 | M |
| **P5** | JS API (SDK + `window.*`) | P2; **Q1 answered** | 05 | M |
| **P6** | Integration tests (workflows + UI smoke + Docker) | P2, P3 (fixtures); P5 for the UI-smoke `window.sgp` path | 06 | M |
| **P7** | Debrief + Librarian/catalogue update | all | — | S |

```
            ┌────────────┐
            │  P1  fixes │  ← fire first; cheap; de-risks everything
            │  + bootstrap│
            └──────┬──────┘
                   │ MERGED FIRST
                   ▼
            ┌────────────┐
            │  P2  tabs  │  ← the capability-driven console shell
            └──────┬──────┘
        ┌──────────┼──────────┬───────────────┐
        ▼          ▼          ▼               ▼
   ┌────────┐ ┌────────┐ ┌──────────┐   ┌──────────┐
   │ P3 wf  │ │ P4 docs│ │ P5 js-api│   │ P6 tests │
   │ io+gal │ │ +drift │ │ ⟂ Q1     │   │ (uses P3 │
   └───┬────┘ └───┬────┘ └────┬─────┘   │  fixtures)│
       │          │           │          └────┬─────┘
       └──────────┴─────┬─────┴───────────────┘
                        ▼
                  ┌──────────┐
                  │ P7 debrief│
                  └──────────┘
```

**Critical path = P1 → P2 → max(P3, P4, P5⟂Q1) → P6 → P7.** P3, P4, P5 are mutually
independent once P2 lands. P5 is additionally gated on Q1 but is **never on the
console's critical path** (the inline script is fully usable without an SDK).

---

## 2. Why these slice boundaries are independent

Everything lives in **one file** (`INDEX_HTML` in `Routes__Index.py`, Decision #1), so
unlike the lab harness the slices are NOT separate folders. The boundaries are
therefore **named regions of the single file plus separate test files**:

| Slice | Owns (in `INDEX_HTML`) | Owns (separate files) |
|-------|------------------------|------------------------|
| P1 | the `<script>` helpers: `bootstrap()`, `authHeaders()`, `request()`, `escHtml()` usage, health badge; the `format` relabel | — |
| P2 | the tab rail + each tab's builder/result pane; the verb→fields table | — |
| P3 | the `workflowIO` region + the `WORKFLOWS` gallery array | bundled `.sgpw.json` fixtures (also tests) |
| P4 | the docs/help pane + contextual `?` popovers | — |
| P5 | the `window.sgp` block + optional `sg-playwright-client.js` route | `sg-playwright-client.js` (if served) |
| P6 | — | `tests/integration/test_Workflows__Gallery.py`, `tests/unit/...`, `tests/deploy/...` |

**Conflict surface:** the single shared file. To keep slices conflict-free, P1 lands
**first and alone** (it touches the most shared helpers); P2 lands the tab scaffold as
one PR; then P3/P4/P5 append into clearly-fenced regions with `<!-- region: workflowIO -->`
style comment markers so diffs don't overlap. P6 touches only test files (zero
conflict with the UI slices).

> This is the key difference from the lab harness: there, agents owned disjoint
> folders. Here, the file is shared, so **sequencing matters more than parallelism** —
> P1 and P2 are gates, P3/P4/P5 fan out only after the scaffold is stable.

---

## 3. Per-slice size & dependencies

| Slice | Size | Lines (UI) | Lines (test) | Critical deps | Branch |
|-------|------|-----------:|-------------:|---------------|--------|
| P1 fixes+bootstrap | S | ~120 | ~80 | — | `claude/pw-ui-p1-fixes-<sid>` |
| P2 tabs | L | ~700 | ~200 | P1 | `claude/pw-ui-p2-tabs-<sid>` |
| P3 workflow io+gallery | M | ~300 | ~150 | P2 | `claude/pw-ui-p3-workflows-<sid>` |
| P4 docs+drift | M | ~250 | ~120 | P2 | `claude/pw-ui-p4-docs-<sid>` |
| P5 js-api | M | ~250 | ~120 | P2; **Q1** | `claude/pw-ui-p5-jsapi-<sid>` |
| P6 integration tests | M | — | ~500 | P2, P3 | `claude/pw-ui-p6-tests-<sid>` |

All branches off `dev`; none push to `dev` directly; each opens a PR (CLAUDE.md git
rules #29-#31). Recommended integration branch `claude/pw-ui-console-<sid>` that the
slice PRs target, merged to `dev` once P1+P2 review clean and the rest stack on top.

---

## 4. Per-agent prompt skeleton

```
Role: Dev (Sonnet) working on the SG Playwright Service.

Task: implement Slice P<N> of the v0.2.64 playwright-test-pages-and-workflows
milestone, per library/dev_packs/v0.2.64__playwright-test-pages-and-workflows/.

Read in order:
  1. /.claude/CLAUDE.md
  2. library/dev_packs/v0.2.64__playwright-test-pages-and-workflows/README.md
  3. .../00__capability-baseline.md   (the facts + bug list + D1-D6)
  4. .../<your slice brief>           (01 / 02+03 / 04 / 05 / 06)
  5. team/humans/dinis_cruz/claude-code-web/06/21/15/playwright-capability-map.md
  6. library/skills/sg-playwright-capabilities/SKILL.md
  7. library/skills/use-sg-playwright/SKILL.md
  8. library/guides/v3.1.1__testing_guidance.md   (P6 only)

Constraints (non-negotiable):
  - ONE file: edits go into INDEX_HTML in
    sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py
    (Decision #1) — no SPA, no build step, no external deps.
  - No new endpoints, no schema changes, no new step verbs (Decision #9).
  - Capability-driven: gate UI on GET /health/capabilities (Decision #2).
  - Auth-mode aware: X-API-Key (direct) vs x-sgraph-access-token (/pw) (Decision #7).
  - HTML-escape EVERY user-echoed string (the ${url} XSS fix).
  - Every request body matches a Schema__* — cite the field; never invent names.
  - Tests: no mocks, no patches; in-memory via _build_fast_api()+_FakeLauncher()
    (register_playwright_service__in_memory does NOT exist — see brief 06);
    real Chromium gated on SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE, skip cleanly.
  - Markdown deliverables: YAML frontmatter, never # ═══ headers.
  - P5 only: if Q1 (JS-API precedent repo) is unanswered, STOP and ask — do not
    guess the API shape.

When done:
  1. Run the acceptance for your slice (§5).
  2. Commit; open a PR to the integration branch. Do NOT merge yourself.
```

---

## 5. Acceptance gates

| Gate | Trigger | Check |
|------|---------|-------|
| **G1** | P1 PR | On a key-protected deployment, badge reads "healthy"; a `"`-containing URL in a label does not break markup; batch render survives a non-array `screenshots`; `format` toggle reads "Render: Image / HTML source". |
| **G2** | P2 PR | Each of Sequence/Inspect/Session/Browser/Debug/Service tabs builds + executes a request; disabled tabs match `capabilities` (e.g. Session greyed when `supports_persistent=false`). |
| **G3** | P3 PR | Build W3 → export → re-import → identical body; "Copy as curl" emits a key-placeholder, not the stored key; gallery loads W1-W9. |
| **G4** | P4 PR | Verb reference lists all 24 verbs; version shown == `/health/info` `service_version` (not v0.1.29); drift test passes. |
| **G5** | P5 PR (post-Q1) | `await window.sgp.run(window.sgp.loadExample('W1'))` renders a result; SDK handles JSON + image/png + text/plain responses. |
| **G6** | P6 PR | `pytest tests/integration/test_Workflows__Gallery.py` passes with real Chromium and **skips cleanly** without it; Docker `test_1..test_6` build job green on `workflow_dispatch`. |
| **G-Final** | integration → dev | Full UI walkthrough; reality-doc D1 flagged to Librarian; debrief filed. |

A failed gate blocks the integration→dev merge, not the next slice's PR.

---

## 6. Risk register

| Risk | Mitigation |
|------|-----------|
| Slices collide in the single `INDEX_HTML` file | P1+P2 are sequential gates; P3/P4/P5 append into fenced `<!-- region -->` blocks; P6 is test-only |
| An agent adds a new endpoint/verb to "make the UI nicer" | Decision #9 + code review; the pack scope is UI/workflow/docs/tests against the existing surface |
| An agent reads `capabilities.json` (v0.1.29) instead of `/health/capabilities` | Decision #2 + G4 version check catches it (shows v0.2.63) |
| Q1 unanswered blocks the milestone | P5 is off the critical path; P1-P4+P6 ship a fully-usable console without any SDK |
| `register_playwright_service__in_memory()` assumed but absent | Brief 06 documents the real `_build_fast_api()` pattern up front; the prompt skeleton repeats it |
| XSS fix missed in one of the 4 echo sites | G1 explicit check + AppSec sign-off (README checklist) |
| Reality-doc D1 silently "fixed" by an agent | Out of scope; the pack flags D1 to the Librarian but edits no reality doc |

---

## 7. What "done" looks like

- `GET /` opens a capability-driven console; visible controls match
  `/health/capabilities`.
- All 21 direct endpoints + the 24-verb language are reachable from the UI.
- Workflows round-trip losslessly (build → export → import) and copy-as-curl.
- In-app docs are generated from the live capability surface (no drift).
- A proposed JS API is documented and — once Q1 lands — implemented additively.
- Integration tests map each gallery workflow to an assertion, gate real Chromium,
  skip cleanly when absent, use no mocks, and a Docker-build job curls the live
  `GET /`.
- A debrief lands under `team/claude/debriefs/` (good-failure / bad-failure) and the
  Librarian is notified that the reality doc is stale on endpoint count + Session (D1).
