# Code review — T2 Frontend hotfix bundle (T2.1 + T2.2)

**Date:** 2026-05-05 (UTC 14)
**Branch:** `dev` @ v0.2.1
**Scope:** Frontend hotfix phases T2.1 (launch-flow three modes) and T2.2 (spec-detail view), plus the BV `/api/amis` follow-up brief.
**Reviewer:** Claude (deep code review)

═══════════════════════════════════════════════════════════════════════════════

## T2.1 — Launch flow: three modes + AMI picker + size + timeout + cost preview

**Commits:** `67ca15e phase-T2.1__FE: launch-form three-mode selector + ami-picker (PARTIAL)`

### Acceptance criteria

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Mode selector renders FRESH / BAKE_AMI / FROM_AMI | ✅ DONE | `sg-compute-launch-form.html:5-29` | 3-card radio grid; FRESH default, `aria-labelledby`, `role="group"` |
| AMI picker conditionally appears for FROM_AMI | ✅ DONE (UI) / ⚠ PARTIAL (data) | `sg-compute-launch-form.css:7-10`, `.html:48-52` | CSS-only show/hide via `.mode-from-ami .from-ami-only`. Picker is a placeholder — no fetch yet (intentional — see BV brief) |
| Size + timeout always visible | ✅ DONE | `sg-compute-launch-form.html:55-72` | Region/instance/hours selects unchanged from prior baseline; always rendered |
| Cost preview banner appears for BAKE_AMI | ✅ DONE | `sg-compute-launch-form.html:32-35`, `.css:30-37` | Static text "≈ 10 min build · ≈ $0.05 / GB / month storage", role=note |
| Submit blocked for invalid combinations | ✅ DONE | `sg-compute-launch-form.js:115-125` `validate()`; `sg-compute-launch-panel.js:44-46` calls validate() before _launch() | Inline error `aria-role="alert"` |
| Snapshot tests cover all three modes | ❌ MISSING | n/a | Debrief admits: "Deferred — no test runner for native ESM Web Components". This was a brief acceptance criterion. Should have been called out as a separate PARTIAL line item, not silently deferred to a paragraph in the debrief |
| Live browser smoke test screenshot in PR | ❌ NOT VISIBLE | n/a | No screenshot or `.png` artefact in commit. Debrief mentions "FRESH mode is fully functional" but no captured evidence; live smoke test acceptance gate not provably exercised |

**Mode-conditional fields wiring:**
- FRESH: name + region + instance + hours + adv ✅
- BAKE_AMI: + AMI name field (`.field-ami-name`) + cost banner ✅
- FROM_AMI: + AMI picker + required-error message ✅

**Submit payload (`sg-compute-launch-panel.js:48-58`):** includes `creation_mode` and `ami_id`. Note: `ami_name` is captured by `getValues()` but **NOT** forwarded into the POST body — for BAKE_AMI mode the AMI name the user typed will be silently dropped on submit. This is a real bug, not just a skipped feature.

### Project-rule violations

- ✅ No build toolchain; native ES modules; plain CSS; Web Components with Shadow DOM (extends `SgComponent`).
- ✅ Three-file pattern present (`.js` + `.html` + `.css` siblings under `_shared/sg-compute-ami-picker/v0/v0.1/v0.1.0/`).
- ✅ Custom element naming `sg-compute-ami-picker` (post-FV2.12 convention).
- ✅ Events on `document` with `{ bubbles: true, composed: true }` (`sg-compute-ami-picker.js:14-17`).
- ✅ ARIA: `role="group"`, `aria-labelledby`, `aria-live="polite"`, `aria-label` on AMI select, `aria-expanded` toggled on the advanced disclosure button.
- ✅ Keyboard nav: radio cards use `:focus-visible` ring (CSS:24).
- ✅ No third-party calls — placeholder uses local CSS tokens.

**Minor:**
- `sg-compute-launch-form.js:166-168` adds a `$$()` helper inside the class for shadowRoot multi-element queries. Reasonable but possibly belongs on the base `SgComponent` — single-occurrence helpers tend to drift.

### Process-rule violations

- ✅ Commit subject correctly tagged `(PARTIAL)`.
- ✅ Backend follow-up brief filed in the same PR: `team/comms/briefs/v0.2.1__hotfix/backend/BV__ami-list-endpoint.md` — proper shape, integration hook documented, references the exact JS callsite (`setSpecId()`).
- ✅ Debrief filed (`team/claude/debriefs/2026-05-05__t2.1__launch-flow-three-modes.md`) with explicit "Status: PARTIAL" header and a "What was NOT done" table.
- ⚠ Live smoke test gate not satisfied — debrief asserts FRESH works end-to-end but no screenshot/artefact attached, and the brief explicitly required it.
- ⚠ Snapshot tests dropped silently in PARTIAL list — they were an acceptance criterion (brief Task 8). Deferral is reasonable (no test runner) but should have been the second PARTIAL bullet in the commit message, not buried in the debrief.
- ✅ No workaround: shipping a placeholder gated behind a real backend brief is the correct root-cause approach.

### Bad decisions / shortcuts

1. **`ami_name` swallowed by the panel.** `getValues()` returns it but `_launch()` body composition drops it. For BAKE_AMI users, this means the form collects data that is silently discarded. Should either be in the payload (under `ami_name` to match a future backend field), or the field should be marked "(not yet wired)" so user expectation is correct. This is the kind of contract-skin that the previous review flagged.
2. **`_currentMode` value `'fresh' | 'bake-ami' | 'from-ami'`** — hyphen-separated. The brief and Schema__Node__Create__Request__Base post-T2.6 uses underscored enum values (`fresh`, `bake_ami`, `from_ami`). The kebab strings will not match a backend enum without translation. No mapping layer exists in the panel — assumed it'll "just work". Will break at integration time.
3. **Constants duplicated again** — see pattern check below. T2.1 modifies `sg-compute-launch-form.js` (which already has its own copy) but doesn't take the chance to consolidate or even add a `// TODO: dedupe` comment.

### Verdict

⚠ **Has issues** — UI scaffolding is honest and well-flagged as PARTIAL; the backend follow-up brief is excellent. But (a) `ami_name` is dropped on submit (real bug), (b) creation_mode kebab-case will likely break at backend integration, (c) snapshot tests silently dropped from acceptance, (d) no smoke test artefact. None of these are blocking ship — but all four are exactly the "claim more than was delivered" pattern.

═══════════════════════════════════════════════════════════════════════════════

## T2.2 — `<sg-compute-spec-detail>` (FV2.4 silently dropped this)

**Commits:** `dc703ed phase-T2.2__FE: sg-compute-spec-detail component (FV2.4 scope cut)`

### Acceptance criteria

| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| `<sg-compute-spec-detail>` exists with three-file pattern | ✅ DONE | `components/sp-cli/sg-compute-spec-detail/v0/v0.1/v0.1.0/{js,html,css}` | All three files; properly registered |
| Click a spec card → detail tab opens | ✅ DONE | `sg-compute-specs-view.js:65-70` dispatches `sp-cli:spec.selected`; `admin.js:67` listens; `admin.js:243-258` opens tab | Note: cards now have a separate "View details" button; clicking the card body itself does **not** open the detail (see issue 1 below) |
| All listed manifest fields render | ⚠ PARTIAL | `sg-compute-spec-detail.html:21-30` and `.js:34-79` | Renders: spec_id, display_name, icon, version, stability, nav_group, capabilities, boot_seconds_typical, extends, create_endpoint_path. **Missing from brief Task 2:** none of the listed fields are missing — this is actually complete for the manifest |
| "Launch node" button opens launch flow with spec_id pre-filled | ✅ DONE (legacy) / ⚠ Coupled to dual-launch issue | `sg-compute-spec-detail.js:88-94`; `admin.js:262-278` opens `<sg-compute-launch-panel>` (the legacy/FV2.5 launch panel, not a new T2.1 launch flow tab) | Dispatches `sp-cli:catalog-launch`. Routes through the existing `_openLaunchTab` which loads `sg-compute-launch-panel`, which embeds `sg-compute-launch-form` — so the new three-mode form **is** rendered. So this works in practice — but it's still the dual-flow architecture flagged in the prior review (T3.2 backlog) |
| Snapshot test for representative spec | ❌ MISSING | n/a | Same gap as T2.1 — no test runner. Not even an attempt; not flagged as PARTIAL |
| Live smoke test screenshot in PR | ❌ NOT VISIBLE | n/a | No screenshot artefact |
| AMI list section labelled clearly | ✅ DONE | `sg-compute-spec-detail.html:43-49` | Visible warning + ref to `GET /api/amis` |
| README link works OR clearly noted | ⚠ PARTIAL | `sg-compute-spec-detail.js:74-85` | Always renders the link unconditionally to `/api/specs/{id}/readme` (which the backend may 404 on). Debrief acknowledges this and calls it "acceptable — better than hiding it." Disagree: it ships a clickable link that 404s. The HTML has a `.sd-readme-placeholder` element ready to use, but `.js:80` always picks the link branch when `spec_id` is truthy — the placeholder is never shown. The brief explicitly said "If the backend doesn't serve this, omit or show a placeholder." This is a soft contract violation |

### Project-rule violations

- ✅ Three-file pattern; one class per file; SgComponent extension.
- ✅ Shadow DOM, custom element naming (`sg-compute-spec-detail`).
- ✅ Events on `document` with `{ bubbles: true, composed: true }` (`sg-compute-spec-detail.js:90-93`, `sg-compute-specs-view.js:66-69`).
- ✅ Plain CSS; uses CSS custom properties / tokens.
- ⚠ **Inline `style="..."` attributes in JS-generated HTML.** `sg-compute-spec-detail.js:62-64` and `.js:69-71` emit raw `style="font-family:monospace;..."` strings inside `innerHTML`. The project rule is plain CSS files, not inline styles. The `.css` file already has `.cap-chip` and `.sd-endpoint` classes — there's no reason these branches don't reuse them. This is small but it's the wrong pattern.
- ✅ ARIA: `role="note"` on AMI placeholder; `aria-label` on detail buttons via the surrounding context. `aria-hidden="true"` on decorative icons. Header buttons have plain text labels ("Launch node →") so no icon-only ARIA needed.
- ⚠ XSS guard: `_esc()` is defined and used for most fields, but `_endpointEl.innerHTML` and `_capsEl.innerHTML` rely on `_esc(c)` inside template literals — fine. But `_extendsList.innerHTML` uses `esc(id)` inside a `<code style="...">` template — the inline style is the issue (rule violation), not the escaping.
- ✅ No third-party calls.

### Process-rule violations

- ⚠ Commit subject says `(FV2.4 scope cut)` but the debrief is **`Status: COMPLETE`**. The phrase "scope cut" in the commit refers to fixing FV2.4's earlier scope cut (correctly), but the parenthetical reads like a PARTIAL marker — it isn't, and that's confusing. It should say `(FV2.4 scope-cut fix)` or just drop it.
- ❌ Snapshot test acceptance criterion silently dropped — debrief does not acknowledge this. T2.1 at least listed it under "What was NOT done." T2.2 just does not mention testing at all.
- ❌ No live smoke test screenshot. Debrief skips the live-smoke-test acceptance gate entirely.
- ⚠ README link: shipped active link to a route the backend doesn't serve. The debrief openly says "if the route 404s the user sees a broken link in a new tab (acceptable)." The brief said placeholder. This is a small workaround masquerading as a feature — a "good failure" would have been: file a backend brief for `/api/specs/{id}/readme` (matching the pattern T2.1 set with BV__ami-list-endpoint.md) and show the placeholder until then. The dev had a working playbook from T2.1 and didn't apply it.
- ✅ Debrief filed with the proper structure.

### Bad decisions / shortcuts

1. **Click target — only "View details" button opens detail, not the whole card.** Brief Task 7: "Wire the click on `<sg-compute-specs-view>` cards — clicking a card opens the detail in a new tab." Implementation only added a secondary button. Cards themselves are still inert as detail-openers (the existing primary "Launch node" still goes straight to launch). This is a UX regression vs the brief's spec — users have to find the secondary button instead of clicking the card.
2. **README link not gated on a follow-up brief.** Should mirror T2.1's pattern: file `BV__spec-readme-endpoint.md`, show placeholder until backend ships. Instead the dev shipped a deliberately-broken link "because it's better than hiding it" — but the brief said the opposite.
3. **Inline styles in JS template literals** when matching CSS classes already exist (see project-rule violations).
4. **`spec.icon || '⬡'`, `spec.stability || 'experimental'`** — defaulting `stability` to `experimental` is dangerous when the field is missing (a missing-stability spec will be silently labelled as experimental — wrong colour badge, misleading metadata). Should fall back to no badge or to a neutral "unknown" class.
5. **Status: COMPLETE in debrief is over-claimed** when README link is broken-by-design, snapshot tests skipped, smoke test missing, and card-click not wired. PARTIAL would be the honest mark.

### Verdict

⚠ **Has issues** — Component scaffolding is solid and the manifest panel is genuinely complete. But the debrief marks this COMPLETE while at least four brief items are partial or skipped (card-click target, snapshot test, smoke test, README placeholder pattern). This is the exact "silent scope cut" pattern the new process rules were meant to prevent. T2.2 is a step backward from T2.1's PARTIAL discipline.

═══════════════════════════════════════════════════════════════════════════════

## Pattern check across both phases

### `INSTANCE_TYPES` / `REGIONS` / `MAX_HOURS` / `COST_TABLE` duplication

**REGRESSED.** Prior review flagged duplicates in two places. Today they live in **three** copies:

- `components/sp-cli/_shared/sg-compute-launch-form/.../sg-compute-launch-form.js:4-6` (the canonical form — modified by T2.1)
- `components/sp-cli/sg-compute-compute-view/.../sg-compute-compute-view.js:13-15` plus a `COST_TABLE` definition (line 29)
- `components/sp-cli/sg-compute-settings-view/.../sg-compute-settings-view.js:16-18`

Plus a fourth, deliberately-different copy in `sg-compute-region-picker.js:16` (`['eu-west-2']` only — explicitly noted "expand when multi-region support lands").

T2.1 modified the launch-form file directly and added new mode constants (`MODE_FRESH`, `MODE_BAKE_AMI`, `MODE_FROM_AMI`) — a **new** local-constants block — without consolidating or even adding a `// TODO: dedupe with sg-compute-compute-view.js`. The duplication has gotten worse, not better.

### Field-name fallbacks (`stack_name || node_id`)

**MIXED.** T2.1/T2.2 themselves did not introduce new fallbacks in the modified files. But:

- `admin.js:264` (`entry.spec_id || entry.type_id`) and `:283` (`stack.spec_id || stack.type_id`, `stack.node_id || stack.stack_name`) remain.
- `sg-compute-launch-form.js:88-100` populate uses `entry?.type_id`, `entry?.default_region` (no `spec_id` fallback). T2.2's `_launch()` dispatches the `spec` object verbatim, which `_openLaunchTab` then resolves via `entry.spec_id || entry.type_id` — so it works only because of the existing fallback.

Net: no new fallbacks introduced in this pair of phases, but neither phase removed any.

### Hardcoded `'running'` state strings

**CLEAN.** No new instances of `'running'`/`"running"` literals in T2.1 or T2.2 source. The shared `node-state.js` helpers (`isRunning`, `nodePillClass`, `podPillClass`, `stateClass`) are used by `sg-compute-cost-tracker`, `sg-compute-user-pane`, `sg-compute-nodes-view`. T2.1/T2.2 didn't touch state logic, so neither regressed nor improved this. No raw state strings introduced.

═══════════════════════════════════════════════════════════════════════════════

## Process-rule application

**Is the team using the new rules?** Mixed — T2.1 yes, T2.2 partially.

| Rule | T2.1 | T2.2 |
|---|---|---|
| PARTIAL marker honestly used | ✅ Commit + debrief title both say PARTIAL | ❌ Debrief says COMPLETE despite README/test/smoke/click gaps |
| Follow-up brief filed for deferred work | ✅ `BV__ami-list-endpoint.md` filed in same PR; properly references the JS hook | ❌ No `BV__spec-readme-endpoint.md` filed for the README link gap; no follow-up brief filed for snapshot tests |
| Live smoke test (screenshot/browser) | ❌ Not in PR | ❌ Not in PR |
| Root-cause vs workaround | ✅ Picker placeholder + backend brief is the right approach | ⚠ README "ship a broken link, it's better than hiding it" is a workaround |
| Commit message matches content | ⚠ Says "FROM_AMI + BAKE_AMI form UI complete" but `ami_name` is dropped on submit | ⚠ Says "Launch node button" works but coupling to legacy launch panel not flagged |

**Trend:** T2.1 demonstrated the correct PARTIAL playbook (mark in commit + debrief + follow-up brief). T2.2 had that playbook in front of it and ignored half of it — silently dropped tests, shipped a broken link instead of a placeholder, marked the result COMPLETE. **The process discipline is regressing within the same PR pair.**

The previous review identified silent scope cuts as the recurring pattern. T2.1 fixed it for one phase. T2.2 reintroduced it the next day.

═══════════════════════════════════════════════════════════════════════════════

## Top 3 issues (cross-cutting)

1. **T2.1: `ami_name` collected by `getValues()` but never forwarded by `sg-compute-launch-panel._launch()`.** Real data-loss bug for BAKE_AMI users. (`sg-compute-launch-form.js:108`, `sg-compute-launch-panel.js:48-58`)
2. **T2.1: `creation_mode` value strings are kebab-case (`bake-ami`, `from-ami`)** but T2.6 backend Safe_Str primitives use underscored enum values. Will not match without translation; nothing in the panel maps them.
3. **T2.2: status mismatch.** Debrief says COMPLETE; in reality (a) snapshot test missing, (b) smoke test missing, (c) card-click not wired — only the secondary button is, (d) README link is a known-broken anchor instead of a placeholder + follow-up brief. Should be PARTIAL with a `BV__spec-readme-endpoint.md` and a card-click follow-up.

═══════════════════════════════════════════════════════════════════════════════

## Overall verdict

**PATCH.** Do not rework — the components are real, the structure is right, and T2.1 set a strong precedent with the BV brief. But ship a small follow-up patch that:

- **T2.1:** include `ami_name` in the launch payload; add a kebab→snake mapping (or change the constants to underscored values up front); document the `creation_mode` values list explicitly.
- **T2.2:** flip the debrief to PARTIAL; file `BV__spec-readme-endpoint.md`; switch the README anchor to a placeholder until that brief lands; wire the card body click (not just the secondary button) per brief Task 7; remove inline `style=` attributes in favour of the existing `.cap-chip` / `.sd-endpoint` CSS classes.
- **Both:** capture browser screenshots and attach to PR before close.

The honest-PARTIAL discipline from T2.1 is the right model — T2.2 needs to be brought back to it before the pattern decays further.
