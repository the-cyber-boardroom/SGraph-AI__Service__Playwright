# v0.2.1 Hotfix — Frontend

**Audience:** the frontend Sonnet team (the dev who shipped FV2.1-FV2.12).
**Read first:** [`../../v0.2.0__sg-compute__architecture/00__README.md`](../../v0.2.0__sg-compute__architecture/00__README.md), then the executive review at [`../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md).

**Stop all new FV2.x phase work until Tier 1 is closed.**

---

## Phase index

Status as of 2026-05-05 14:30 UTC.

### Tier 1 — Runtime breakage

| # | File | Status |
|---|------|--------|
| T1.7 | [`T1_7__ui-imports-runtime-break.md`](T1_7__ui-imports-runtime-break.md) | ✅ DONE (commit `c79770d`) — Option B (`/ui/` mount in `Fast_API__Compute`) chosen with rationale documented |

### Tier 2 — Contract violations

| # | File | Status |
|---|------|--------|
| T2.1 | [`T2_1__launch-flow-three-modes.md`](T2_1__launch-flow-three-modes.md) | ⚠ PARTIAL textbook (commit `67ca15e`) — 4 of 5 brief items shipped; AMI picker is flagged placeholder; [`backend/BV__ami-list-endpoint.md`](../backend/BV__ami-list-endpoint.md) filed. **2 hidden bugs** found in review (see T2-FE-patch). |
| T2.2 | [`T2_2__spec-detail-view.md`](T2_2__spec-detail-view.md) | ⚠ Over-claimed COMPLETE (commit `dc703ed`) — 4 real gaps under "COMPLETE": card-click not wired; README link known-broken anchor; snapshot omitted; no smoke screenshot. **Fix in [`T2_FE-patch__ami-spec-detail-fixes.md`](T2_FE-patch__ami-spec-detail-fixes.md)** |
| T2.3 | [`T2_3__a11y-keyboard-and-contrast.md`](T2_3__a11y-keyboard-and-contrast.md) | ✅ DONE (commit `ae5fca2`) — `--text-3` raised to ≥4.65:1; keyboard nav added |
| T2.4 | [`T2_4__settings-bus-dual-dispatch.md`](T2_4__settings-bus-dual-dispatch.md) | ✅ DONE (commit `ae5fca2`) — settings-bus dual-dispatch wired |
| T2.5 | [`T2_5__caller-ip-consumer.md`](T2_5__caller-ip-consumer.md) | ✅ DONE (commit `ae5fca2`) — caller-ip consumer; [`backend/BV__caller-ip-endpoint.md`](../backend/BV__caller-ip-endpoint.md) filed |

### Tier 3 — Integration cleanup

| # | File | Status |
|---|------|--------|
| T3.1 | [`T3_1__user-tree-api-migration.md`](T3_1__user-tree-api-migration.md) | ✅ DONE (commit `8afe5b7`, bundled) |
| T3.2 | [`T3_2__collapse-dual-launch-flows.md`](T3_2__collapse-dual-launch-flows.md) | ✅ DONE (commit `8afe5b7`, bundled) |
| T3.3 | [`T3_3__cosmetic-rename-leftovers.md`](T3_3__cosmetic-rename-leftovers.md) | ✅ DONE (commit `8afe5b7`, bundled) |
| T3.4 | [`T3_4__hardcoded-instance-types-cost-table.md`](T3_4__hardcoded-instance-types-cost-table.md) | ✅ DONE (commit `8afe5b7`, bundled) — `shared/launch-defaults.js` |
| T3.5 | [`T3_5__field-name-pinning.md`](T3_5__field-name-pinning.md) | ✅ DONE (commit `8afe5b7`, bundled) |

> **Process note:** T3.1-T3.5 shipped as ONE PR (`8afe5b7`). Cleanup-class work is acceptable to bundle but the debrief should flag the bundle as a deliberate process choice. Net result is positive — all 5 cleanup items closed; debriefs backfilled.

### Frontend follow-up patches (filed 2026-05-05 14:30)

| # | File | Why |
|---|------|-----|
| **T2-FE-patch** | [`T2_FE-patch__ami-spec-detail-fixes.md`](T2_FE-patch__ami-spec-detail-fixes.md) | T2.1 `ami_name` data-loss + `creation_mode` enum-case + T2.2 4 hidden gaps |

---

## Hard rules (binding every PR)

- No build toolchain. Native ES modules. Plain CSS. Web Components with Shadow DOM.
- Three-file pattern: `.js` + `.html` + `.css` siblings under `{name}/v0/v0.1/v0.1.0/`.
- Custom-element naming: `sg-compute-*` (FV2.12 has shipped). Any new component uses `sg-compute-*`.
- Events on `document` with `{ bubbles: true, composed: true }`.
- WCAG AA contrast, keyboard nav, ARIA labels on icon-only controls.
- **No third-party calls** from the dashboard.
- Branch `claude/t1-fe-hotfix-{session-id}` (Tier 1) or `claude/t2-fe-{N}-{session-id}` / `claude/t3-fe-{N}-{session-id}`.
- PR title `phase-T1__FE-runtime-fix` (Tier 1) or `phase-T2.{N}__FE: {summary}` / `phase-T3.{N}__FE: {summary}`.
- Each PR ends with a debrief in `team/claude/debriefs/`.
- CLAUDE.md rule 9 (no underscore-prefix) is **Python only**. JS keeps `_foo()`.

## New process rules (apply from now on)

- **`PARTIAL` is a valid debrief status.** Any descope = follow-up brief in same PR.
- **Live smoke test** as an acceptance criterion on every phase. Browser must render the change with no console errors before claiming done.
- **"Stop and surface"** if you're working around a problem instead of fixing the root cause.
- **Commit messages match content.** No "all X" claims when half is done.

---

## Recommended execution order

1. **T1.7** — runtime fix first; spec detail panels are likely broken in production.
2. **T2.1 → T2.2 → T2.3 → T2.4 → T2.5** — contract violations (FV2.5 + FV2.4 are biggest gaps).
3. **T3.1 → T3.2 → T3.3 → T3.4 → T3.5** — cleanup.
4. Resume planned FV2.13 + onwards only after Tier 1 + Tier 2 close.

See [`SESSION_KICKOFF.md`](SESSION_KICKOFF.md) for the paste-into-fresh-session brief.
