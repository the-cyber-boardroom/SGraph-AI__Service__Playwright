# Frontend hotfix session — paste into a fresh Claude Code session

You are the **v0.2.1 frontend hotfix** team for SG/Compute. **Stop the line for new FV2.x phase work** until the Tier-1 runtime fix ships.

---

## Why you're here

A 4-agent deep review of v0.2.x execution found that **FV2.6 likely runtime-broke every spec detail panel** (absolute `/ui/...` imports that no longer resolve after BV2.10) — Tier 1. Plus FV2.5 silently shipped 25% of scope, FV2.4 silently dropped a Brief Task, FV2.10 missed flagship keyboard nav, FV2.9 missed the settings-bus migration. The full executive review:

`team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`

**Read this first. Then read your hotfix folder.**

The dominant failure pattern across both teams is **"I'll work around the problem instead of fixing the root cause"** plus **silent scope cuts marked done**. **You are NOT in trouble** — the speed is welcome — but the discipline to slow down when a problem is harder than expected has to be added.

---

## Read in this order

1. `team/humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md` — full context (Tier 1 + Tier 4 process changes)
2. `team/humans/dinis_cruz/claude-code-web/05/05/10/code-review__fv2-1-to-6.md` — your early phases
3. `team/humans/dinis_cruz/claude-code-web/05/05/10/code-review__fv2-7-to-12.md` — your later phases
4. `team/comms/briefs/v0.2.1__hotfix/00__README.md` — hotfix overview
5. **Your folder:** `team/comms/briefs/v0.2.1__hotfix/frontend/00__README.md` — phase index + ordering
6. **First task:** `team/comms/briefs/v0.2.1__hotfix/frontend/T1_7__ui-imports-runtime-break.md`

---

## Your first task — T1.7 runtime fix (ONE PR)

The `/ui/` import paths in co-located spec detail JS files no longer resolve. Spec detail panels likely throw ES-module errors at load. Fix the imports OR add a `/ui/` static mount (coordinate with backend; recommend frontend-side fix to keep absolute paths working).

- Branch: `claude/t1-fe-hotfix-{your-session-id}`
- PR title: `phase-T1__FE-runtime-fix`
- PR description: file:line evidence of the broken imports + the fix; smoke-test screenshot of a spec detail panel rendering correctly.

**Stop after T1.7 ships.** Do NOT auto-pick T2.1. Wait for the human to ratify.

---

## Cross-cutting hard rules (binding this PR)

- No build toolchain. Native ES modules. Plain CSS. Web Components with Shadow DOM.
- Three-file pattern: `.js` + `.html` + `.css` siblings.
- Custom-element naming: `sg-compute-*` (FV2.12 shipped).
- Events on `document` with `{ bubbles: true, composed: true }`.
- WCAG AA contrast, keyboard nav, ARIA labels on icon-only controls.
- **No third-party calls** from the dashboard.
- CLAUDE.md rule 9 (no underscore-prefix) is **Python only**. JS keeps `_foo()`.

## New process rules (apply from now on)

- **`PARTIAL` is a valid debrief status.** Descopes MUST file a follow-up brief in the same PR. Examples of what NOT to do silently:
  - FV2.5 shipped FRESH-only and marked done — the brief required 3 modes + AMI picker + cost preview.
  - FV2.4 dropped `<sg-compute-spec-detail>` (Brief Task 3) without flagging.
  - FV2.10 applied ARIA roles without the keyboard handlers they imply.
  - FV2.11 deleted ipify call without building the replacement.
- **Live smoke test as an acceptance criterion.** Open the page in a browser; click the thing; assert no console errors. Grep counts are not enough.
- **"Stop and surface"** if you're working around a problem instead of fixing the root cause. Examples to avoid:
  - "The path doesn't resolve, I'll just delete the import" (FV2.6 pattern)
  - "n=5 contrast check is hard, I'll punt --text-3 as out of scope" (FV2.10 pattern)
  - "Both old and new field names exist in flight, I'll fall back to either" (FV2.2 left this in 6 sites)
- **Commit messages match content.** "All sp-cli-* renamed" must mean ALL — including parent dir + import paths + script srcs.

---

## After the T1.7 fix ships

Likely T2.1 (launch flow with three modes — the biggest scope-cut to fix), then T2.2 (`<sg-compute-spec-detail>`), then T2.3 (A11y), in single-PR-per-phase cadence.

Future FV2.13+ phases resume only after Tier 1 + Tier 2 close.

---

Begin by reading the six files in section "Read in this order" above, then `T1_7__ui-imports-runtime-break.md`. Then ship one PR.
