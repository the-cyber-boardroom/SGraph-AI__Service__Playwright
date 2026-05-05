# v0.2.1 Hotfix — Frontend

**Audience:** the frontend Sonnet team (the dev who shipped FV2.1-FV2.12).
**Read first:** [`../../v0.2.0__sg-compute__architecture/00__README.md`](../../v0.2.0__sg-compute__architecture/00__README.md), then the executive review at [`../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md).

**Stop all new FV2.x phase work until Tier 1 is closed.**

---

## Phase index

### Tier 1 — Runtime breakage (ship as one PR)

| # | File | What it fixes |
|---|------|---------------|
| T1.7 | [`T1_7__ui-imports-runtime-break.md`](T1_7__ui-imports-runtime-break.md) | Co-located spec detail JS uses absolute `/ui/...` imports that no longer resolve after BV2.10 — likely runtime break for every spec detail panel |

### Tier 2 — Contract violations (one PR each)

| # | File | What it fixes |
|---|------|---------------|
| T2.1 | [`T2_1__launch-flow-three-modes.md`](T2_1__launch-flow-three-modes.md) | FV2.5 silently shipped 25% of scope (FRESH-only); ship the three-mode selector + AMI picker + size + timeout + cost preview |
| T2.2 | [`T2_2__spec-detail-view.md`](T2_2__spec-detail-view.md) | FV2.4 silently dropped `<sg-compute-spec-detail>` (Brief Task 3) |
| T2.3 | [`T2_3__a11y-keyboard-and-contrast.md`](T2_3__a11y-keyboard-and-contrast.md) | FV2.10 missing flagship keyboard nav; contrast sampled n=1 not n=5; `--text-3` token at 3.8:1 fails AA |
| T2.4 | [`T2_4__settings-bus-dual-dispatch.md`](T2_4__settings-bus-dual-dispatch.md) | FV2.9 missed `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` migration in `shared/settings-bus.js`; spec doc lists it RESERVED (wishful) |
| T2.5 | [`T2_5__caller-ip-consumer.md`](T2_5__caller-ip-consumer.md) | FV2.11 deleted ipify call without replacement; build the backend `/catalog/caller-ip` consumer (and ticket the backend route) |

### Tier 3 — Integration cleanup (one PR each)

| # | File | What it fixes |
|---|------|---------------|
| T3.1 | [`T3_1__user-tree-api-migration.md`](T3_1__user-tree-api-migration.md) | `user/user.js` still calls `/catalog/types` and `/catalog/stacks` — only admin tree was migrated in FV2.2 |
| T3.2 | [`T3_2__collapse-dual-launch-flows.md`](T3_2__collapse-dual-launch-flows.md) | Dashboard has TWO launch flows; FV2.4 "Launch node" routes to LEGACY panel, bypassing FV2.5 |
| T3.3 | [`T3_3__cosmetic-rename-leftovers.md`](T3_3__cosmetic-rename-leftovers.md) | FV2.12 missed parent dir `components/sp-cli/`; 38 import paths still read it; `user/index.html` references deleted directories |
| T3.4 | [`T3_4__hardcoded-instance-types-cost-table.md`](T3_4__hardcoded-instance-types-cost-table.md) | `INSTANCE_TYPES` / `REGIONS` / `MAX_HOURS` / `COST_TABLE` hardcoded in two places (already drifted) |
| T3.5 | [`T3_5__field-name-pinning.md`](T3_5__field-name-pinning.md) | `admin.js` reads `stack.node_id || stack.stack_name` at 6+ sites — encodes migration ambiguity |

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
