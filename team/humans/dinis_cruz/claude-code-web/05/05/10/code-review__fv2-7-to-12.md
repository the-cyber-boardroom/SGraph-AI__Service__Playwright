# Frontend Code Review — FV2.7 → FV2.12

**Scope:** later frontend phases shipped on `dev` since v0.2.0. Branch synced to dev @ v0.2.1 (commit `95cbfa6` head, 2026-05-05).
**Reviewer:** Claude (read-only)
**Date:** 2026-05-05

Phases reviewed (in order shipped, not numeric): FV2.9 (00:18), FV2.10 (00:23), FV2.11 (00:26), FV2.7 (01:10), FV2.8 (01:15), FV2.12 (07:33).

---

## FV2.7 — Pods tab via control-plane proxy

**Commits:** `162077d` FV2.7 — pods tab via control-plane proxy (BV2.3 unblock)
**Files touched:** `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-nodes-view/v0/v0.1/v0.1.0/sp-cli-nodes-view.js` (97 ±). Now lives at `.../sg-compute-nodes-view/.../sg-compute-nodes-view.js` after FV2.12.

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Pods tab calls control plane (`/api/nodes/{id}/pods/...`) not sidecar | ✅ DONE | `sg-compute-nodes-view.js:369` (`apiClient.get('/api/nodes/{id}/pods/list')`), `:476` (`...pods/{name}/logs?tail=200`), `:622` (live polling) |
| Iframe tabs (Terminal, Host API) still go direct | ✅ DONE | `<sg-compute-host-shell>` and `<sg-compute-host-api-panel>` panels embedded; both still build sidecar URLs internally |
| Smoke test passes | ⚠ PARTIAL | Debrief claims "SHIPPED" but no automated/playwright test added; manual smoke not documented |
| Snapshot tests updated | ❌ MISSING | No snapshot test infrastructure exists in repo (`find . -name "*snapshot*"` empty); brief criterion is meaningless against current state |
| `/pods/{name}` GET migrated | ⚠ PARTIAL | Brief listed it; only `list`, `logs` migrated. Pod detail (`/pods/{name}`), pod stats (`/pods/{name}/stats`), pod stop/start NOT migrated. Pod stats still hit sidecar directly at `:453`. |

### Project-rule violations

- None new. Direct sidecar `fetch()` for pod stats and host status retained — debrief acknowledges this and frames it as "no proxy yet".

### Integration concerns

1. **Sidecar API key plumbing (HIGH).** `Pod__Manager._sidecar_client` (`sg_compute/core/pod/Pod__Manager.py:31`) reads the sidecar API key from env var `SG_COMPUTE__SIDECAR__API_KEY`. The dashboard, in contrast, holds a **per-node** `host_api_key` retrieved at launch time and stored in localStorage. The control plane never sees that per-node key. If `SG_COMPUTE__SIDECAR__API_KEY` is unset (or wrong), `Sidecar__Client._get('/pods/list')` will get 401 from the sidecar and `r.raise_for_status()` will throw, manifesting in the dashboard as "Unreachable" / "Loading…" state. There is no test in `Pod__Manager` that exercises a real sidecar; the loop is only proven against an in-memory mock. **This is the foreseeable post-deploy regression.**
2. **`_renderContainers` schema-bridging hack.** Lines 426–427 read `c.pod_name || c.name || ''` and `c.state || c.status || ''`. The `||` fallback to legacy fields is a self-described one-release back-compat shim, but there is no comment marking it as removable or a tracking issue. It will silently mask schema drift in either direction.
3. **`_portLinks` regex is brittle.** New parser `match(/:(\d+)->(\d+)/)` ignores the `proto` (tcp/udp), ignores IPv6-bracketed bind addresses, and silently drops unmatched entries. Old dict-form was structured; new string-form parsing is heuristic. No unit test covers it.
4. **Host stats and pod stats still cross-origin.** Comment at `:418` calls this out, but it means the dashboard is still subject to CORS and per-node API key auth for those calls. `fetch(`${base}/host/status`, ...)` at `:294` and `:370` and `${base}/pods/{name}/stats` at `:453`. The "everything except iframe goes through control plane" goal is **not yet achieved** — the brief's "Notes" section asserts it will be, but it isn't.

### Bad decisions / shortcuts

- **Removed the `if (!base) { ... 'No host URL' ... }` early-return** in `_fetchContainers` (was at top of method pre-FV2.7). Now even if no sidecar URL is known the call still fires `apiClient.get('/api/nodes/{id}/pods/list')` which is correct; but the host-status sub-call quietly resolves to `null` via `.catch(() => null)`, hiding errors that previously surfaced.
- **`role="listitem"` added to pod rows but no `role="list"` on the container** in this commit (only added later in FV2.10 which beat FV2.7 in time but logically follows). Net result is fine; ordering of merges is suspect.

**Verdict:** ⚠ Has issues — works for happy path, but sidecar-key mismatch is a likely production failure mode and the brief's `/pods/{name}` + `/pods/{name}/stats` migration was silently dropped.

---

## FV2.8 — verify zero `/containers/*` references

**Commits:** `860d5e3` FV2.8 — confirm zero /containers/* URL references in dashboard
**Files touched:** 1 CSS comment, 1 reality-doc, 1 debrief.

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `grep -rn "/containers/" api_site/` returns zero | ✅ DONE | Verified at review time — zero hits |
| `container_count` field absent | ✅ DONE | Verified — zero hits |
| "Container" UI labels replaced with "Pod" | ✅ DONE | "Pods" tab label, "No pods running" empty state, `aria-label="Refresh pods"`. Note: internal IDs `tab-containers` / `panel-containers` / `data-tab="containers"` retained — debrief acknowledges as out-of-scope |
| Browser DevTools Network-tab smoke test | ❌ MISSING | Debrief lists it under acceptance but provides no evidence beyond grep |
| Reality doc updated | ✅ DONE | `team/roles/librarian/reality/sg-compute/index.md` updated as claimed |

### Project-rule violations

None.

### Integration concerns

- The CSS comment edit and reality-doc edits are the only code change. The verification was a grep sweep, which is fine — but the brief's "Browser DevTools verification" was skipped.

### Bad decisions / shortcuts

- **Internal routing keys not renamed.** `data-tab="containers"`, `id="tab-containers"`, `id="panel-containers"` and the JS check `if (name === 'containers')` (`sg-compute-nodes-view.js:315`) all still say "containers". This is a tiny tech-debt item the dev intentionally deferred. Debrief documents it. Acceptable, but the user-visible label / internal-key drift will trip up the next person who edits the tab.

**Verdict:** ✅ Solid (with one minor scope gap: no DevTools network verification documented).

---

## FV2.9 — event vocabulary; `sp-cli:plugin:*` → `sp-cli:spec:*`

**Commits:** `89c90dd` FV2.9 — event vocabulary; sp-cli:plugin:* → sp-cli:spec:*
**Files touched:** 11 (1 spec doc + admin.js + events-log + 8 plugin cards).

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 8 per-spec card emitters dual-dispatch `spec:` + `plugin:` | ✅ DONE | Verified — all 8 cards under `sg_compute_specs/{spec}/ui/card/.../sg-compute-{spec}-card.js` emit both events; all 8 added `spec_id` to STATIC |
| `admin.js` listens for both forms | ✅ DONE | `admin.js:108-110` — both registrations in catalogue listener |
| `FAMILIES` map enumerates every event with status | ✅ DONE | `sg-compute-events-log.js` FAMILIES extended; `// DEPRECATED` markers on `plugin:*` lines and stack-* aliases. Note: `RESERVED` status not used in code, only in spec doc |
| `library/docs/specs/v0.2.0__ui-event-vocabulary.md` exists | ✅ DONE | 95 lines, well-structured, documents Catalogue / Node / Launch / Settings / Auth / Diagnostics families with Status (ACTIVE / DEPRECATED / RESERVED) |
| `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` migrated in settings-bus | ❌ MISSING | `shared/settings-bus.js:66` still dispatches `'sp-cli:plugin.toggled'` only. Spec doc lists `sp-cli:spec.toggled` as RESERVED — meaning **the brief Part 1 task #4 was not done**. Card emitters migrated; settings-bus did NOT. |
| Snapshot tests updated | ❌ MISSING | None exist |

### Project-rule violations

- **`sp-cli:plugin.toggled` migration missed (brief task 1.4).** Brief explicitly required: *"In `sp-cli:settings.toggled` family — `sp-cli:plugin.toggled` becomes `sp-cli:spec.toggled` (same back-compat dance)."* The dev only added `sp-cli:spec.toggled` to the FAMILIES map and to the spec doc as RESERVED, but did not actually wire any emitter. This is a **silently dropped requirement**.

### Integration concerns

1. **Spec doc references obsolete file paths.** The v0.2.0 spec doc lists emitters as `sp-cli-{spec_id}-card.js` and `sp-cli-stacks-pane.js`. After FV2.11 (deletes stacks-pane) and FV2.12 (renames to `sg-compute-*`), these paths are stale on the day they were published. The doc was not updated when the rename followed.
2. **Spec doc still shows `sp-cli-stacks-pane.js` as an emitter** for `sp-cli:node.selected` — but that file was deleted in FV2.11. Same-day, conflicting docs.
3. **8 cards is correct** for current count but spec doc claims "12 spec cards" in the "Tasks summary" — the brief said 12. Only 8 exist (docker, podman, elastic, vnc, prometheus, opensearch, neko, firefox). The other 4 from the brief (linux, etc.) don't exist as cards. Brief was wrong; dev did the right thing for 8 but didn't flag the discrepancy.

### Bad decisions / shortcuts

- **`STATIC` retains both `spec_id` AND `type_id` with identical values** (e.g. `{ spec_id: 'docker', type_id: 'docker', ... }`). Brief did not require keeping `type_id`; it's deprecated terminology. Should have been a TODO/comment.
- **Card files were NOT renamed in FV2.9** (still `sp-cli-{name}-card.js`); they got renamed in FV2.12. This creates a window where the file name says "plugin" but the emitter says "spec". Tolerable.

**Verdict:** ⚠ Has issues — `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` emitter migration was dropped. Spec doc has stale paths from same-day FV2.11/FV2.12 churn.

---

## FV2.10 — A11y pass: tablist, keyboard access, focus rings

**Commits:** `18bc143` FV2.10 — A11y pass: tablist, keyboard access, focus rings
**Files touched:** 6 (3 components × 2 files avg).

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| ARIA `role="tablist"` on `sp-cli-nodes-view` tabs | ✅ DONE | `sg-compute-nodes-view.html:31` |
| Each tab `role="tab"`, `aria-selected`, `aria-controls`, `tabindex` | ⚠ PARTIAL | `role="tab"`, `aria-selected`, `aria-controls` present; **`tabindex="0"` NOT set on individual tabs** (defaults to natural `<button>` focus). For roving-tabindex pattern this would be wrong; native button focusability covers it weakly. Acceptable but not what the brief specified. |
| Panels `role="tabpanel"`, `aria-labelledby`, `tabindex="0"` | ✅ DONE | `:34-72` |
| Keyboard nav: ←/→/Home/End for tab switching | ❌ **MISSING** | Brief explicitly required arrow-key tab switching. Search of `sg-compute-nodes-view.js` for `ArrowLeft`/`ArrowRight`/`Home`/`End`: **zero hits**. Only the node-row Enter/Space handler exists. The flagship a11y deliverable is incomplete. |
| Icon-only buttons get `aria-label` | ✅ DONE | All 10 icon buttons (collapse ◀, refresh ↺, close ✕, eye 👁, copy ⎘, log 📋, etc.) carry `aria-label` |
| Spec cards in compute-view: `role="button"`, keyboard | ✅ DONE | `sg-compute-compute-view.js:113-134`; Enter/Space handler present; `aria-pressed`, `aria-disabled`, `aria-hidden` on icon all wired |
| `:focus-visible` rules across components | ⚠ PARTIAL | Added to nodes-view (.node-row, .api-key-btn, .ct-log-btn, .btn-live-log), compute-view (.spec-card), left-nav (.nav-item). NOT added to other components (storage-viewer, vault-picker, region-picker, top-bar, etc.). Brief said "everywhere"; actual coverage is the 3 components touched in this commit. |
| Manual keyboard-only smoke test | ❌ MISSING | No evidence in debrief beyond claim |
| Contrast check on 5 components | ⚠ PARTIAL | Debrief mentions one finding (`--text-3` is ~3.8:1, fails AA body, passes AA large) but does not list 5 components or report numbers per component. Deferred. Stability badges (the brief's specific concern: "experimental" amber on dark) — not measured |
| Snapshot tests updated | ❌ MISSING | None exist |

### Project-rule violations

- **Native plain CSS, native ES modules:** Compliant. No new build dependency.
- **WCAG AA contrast claim is unsubstantiated.** Debrief admits `--text-3` fails 4.5:1 body-text and was punted ("tokens shared with sg-layout; out of scope"). This means the "WCAG AA baseline" goal is **not actually met**.

### Integration concerns

1. **Keyboard tab-switching missing.** Users tabbing through the panel will still tab through every button (default Tab order); the proper roving-tabindex tablist pattern (Tab into the rail once, arrows to switch) is not implemented. This is a meaningful a11y gap.
2. **`aria-current="page"` on left-nav** is technically wrong (these are app views not pages); debrief flags it but defers.
3. **`role="list"` on `.ct-list` was added** but pod rows are not children of an explicit `<ul>` / `role="list"` carrier in older snapshots; rendering still works because role mapping is dynamic. Fine.

### Bad decisions / shortcuts

- **Brief task 5 (contrast check) was effectively skipped.** Only `--text-3` measured; no per-badge measurement of `experimental` on dark, which the brief specifically called out.
- **No global `:focus-visible` rule** in `shared/ec2-tokens.css` — only piecemeal per-component additions. A single `*:focus-visible { outline: ... }` reset in shared tokens would cover everything; the dev added 6 redundant per-element rules.
- **`aria-disabled` set without disabling click handler.** Soon-cards: `if (!spec.soon) card.addEventListener('click', ...)` — so clicks ARE skipped. Good. But pointer-cursor styling is removed via `.spec-card--soon { cursor: default }`. Consistent.

**Verdict:** ⚠ Has issues — flagship deliverable (arrow-key tab switching) NOT implemented; contrast check sampled n=1 not n=5. Real value delivered (ARIA roles, aria-labels, focus rings on 3 components) but the brief overshoots what shipped.

---

## FV2.11 — delete legacy components + external call

**Commits:** `53d2905` FV2.11 — delete sp-cli-stacks-pane; remove api.ipify.org call
**Files touched:** 8 (2 admin + 5 launch-form + 3 stacks-pane deletes).

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `components/sp-cli/sp-cli-stacks-pane/` deleted | ✅ DONE | Path absent; `find` empty |
| `shared/catalog.js` deleted | ✅ DONE | File absent (FV2.3 actually did this; FV2.11 brief's task #3 was already moot, dev correctly skipped) |
| `api.ipify.org` call removed | ✅ DONE | `_fetchBrowserIp()` deleted; `grep -rn "ipify"` returns zero |
| Replacement for ipify (Option A backend `/catalog/caller-ip`, or Option B local heuristic) | ❌ **MISSING** | Brief required either Option A or Option B as a replacement. Dev chose **option C: just delete the row entirely with no replacement**. The Advanced section now has a `.ip-note` advisory but the actual "Your browser IP: X" field is gone. This is a silent scope reduction. |
| No third-party calls from dashboard | ✅ DONE | Sweep clean |
| Smoke test: launch form still detects caller IP | ⚠ N/A | Caller IP detection moved server-side per FV2.5 (`caller_ip` auto-detected by backend). Dashboard no longer needs to know it. Functionally fine, but brief's smoke criterion is now meaningless. |
| Snapshot tests updated | ❌ MISSING | None exist |

### Project-rule violations

- None.

### Integration concerns

1. **`<sp-cli-stacks-pane>` querySelector remained in `admin.js` for one commit-cycle** — fixed in this commit (deleted). Good.
2. **Operator IP no longer visible in the form.** Pre-FV2.5, the operator could see "your browser IP is X" and tick "Open access" to allow it. Post-FV2.5 + FV2.11, that visibility is gone. Backend handles `caller_ip` now, but a power user wanting to verify what IP the SG will whitelist has no UI affordance. Minor UX regression — not flagged anywhere.
3. **`.ip-info` and `.ip-note` CSS retained** even though `.ip-row` deleted — orphan classes if `.ip-info` block has no `.ip-row` children. Cleanup incomplete.

### Bad decisions / shortcuts

- **Replacement skipped (silent scope reduction).** The brief offered Option A (preferred) or Option B (fallback). Dev chose neither and just removed the row. Should have either filed a backend ticket for `/catalog/caller-ip` or added the local heuristic. Debrief justifies this with "FV2.5 already moved IP detection server-side" — which is true but is a legitimate brief-reading judgement call that should have been escalated, not silently absorbed.

**Verdict:** ⚠ Has issues — privacy fix done correctly (good); replacement for the deleted feature not delivered (silently dropped). Net positive.

---

## FV2.12 — cosmetic `sp-cli-*` → `sg-compute-*` web-component prefix rename

**Commits:** `0991ce0` FV2.12 — sp-cli-* → sg-compute-* web component prefix rename
**Files touched:** 146 (140+ git renames + 6 modifications).

### Acceptance criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `grep -rn "sp-cli-" api_site/` returns zero (active code) | ✅ DONE | Verified — zero hits in `.js`/`.html`/`.css` for tag/class names. (`sp-cli:` event-name prefix intentionally retained per commit message and spec — NOT a tag/class.) |
| `git mv` for every `sp-cli-{name}/` directory | ⚠ PARTIAL | All **leaf** dirs renamed (e.g. `sp-cli-nodes-view/` → `sg-compute-nodes-view/`); but **parent dir `components/sp-cli/` was NOT renamed** to `components/sg-compute/`. So import paths now read `components/sp-cli/sg-compute-nodes-view/...` — visually jarring, demonstrably incomplete |
| `class SpCli{Name}` → `class SgCompute{Name}` | ✅ DONE | `grep -rn "SpCli"` zero hits |
| `customElements.define('sp-cli-...', ...)` → `'sg-compute-...'` | ✅ DONE | All 30+ defines updated |
| HTML/CSS sibling tag refs updated | ✅ DONE | grep clean |
| `<script type="module">` tags in `admin/index.html` and `user/index.html` updated | ✅ DONE | 23 + 8 src paths updated; tags themselves switched (`<sg-compute-launch-modal>` etc.) |
| `document.createElement` / `querySelector` with old tags updated | ✅ DONE | `admin.js:296-297` now query `sg-compute-compute-view` and `sg-compute-nodes-view` |
| `_shared/sg-remote-browser` family untouched | ✅ DONE | Confirmed |
| Per-spec UI swept (`sg_compute_specs/{spec}/ui/`) | ✅ DONE | All 8 spec card files renamed and class names updated; detail UIs likewise |
| Snapshot tests pass | ❌ N/A | No snapshot tests exist |
| Manual smoke-test of every view | ❌ MISSING | Debrief makes the claim; no evidence |

### Project-rule violations

- **Naming-rule consistency.** Project rule 20 normalises `SGraph-AI` → `SGraph_AI` for Python identifiers. Web-component custom-element names are kebab-case so the rule applies vacuously here; no violation.

### Integration concerns

1. **Parent directory `components/sp-cli/` not renamed.** All imports still read `../components/sp-cli/sg-compute-...`. This is the most visible loose end. Brief is silent on the parent dir but the spirit (cosmetic rename to drop sp-cli) is incomplete. Will trip up the next grep. Spec UIs at `sg_compute_specs/{spec}/ui/` similarly retain `import '/ui/components/sp-cli/_shared/sg-compute-...'` paths.
2. **`user/index.html` references THREE non-existent components.** `sg-compute-launch-modal`, `sg-compute-stack-detail`, `sg-compute-vault-activity` are all in `<script type="module" src=...>` tags in `user/index.html:37,39,40` AND in `<sg-compute-launch-modal></sg-compute-launch-modal>` markup at `:31`. The corresponding directories DO NOT EXIST in `components/sp-cli/`. These were deleted long ago in commit `510337d cleanup(4.2): delete four deprecated components`. The FV2.12 sed-rename happily updated dead `<script src>` paths from `sp-cli-launch-modal` → `sg-compute-launch-modal` without noticing the files don't exist. **Sweep methodology missed verification step.** Result: opening `/user/` will produce 404s in the browser console for these three modules. Pre-existing bug surfaced (not amplified) by FV2.12.
3. **`sp-cli:` event names intentionally preserved** per commit message — this is correct per the spec doc (event vocabulary is a separate namespace, slated for removal at v0.3.0 with the deprecated alias window). Documented in `library/docs/specs/v0.2.0__ui-event-vocabulary.md`. Defensible.
4. **localStorage keys preserved** (`sp-cli:settings:v3`, `sp-cli:vault:*`, etc.) — also intentional to avoid migrating user state. Good. Spec doc should mention this; it doesn't.

### Bad decisions / shortcuts

- **No verification step beyond `git mv` + sed.** A `for tag in $(grep -oh 'sg-compute-[a-z-]*' admin/*.html); do test -d components/sp-cli/$tag || echo MISSING $tag; done` would have caught the dead `user/index.html` script tags in seconds. The dev did not run any such check.
- **Parent `components/sp-cli/` retained** without comment — should either rename the parent or document why it's kept (lock-step with a future move? deferred to FV2.13?). FV2.13 brief is `dashboard-move`; could plausibly fold this in but that's not stated.
- **Missing spec card directories.** `find sg_compute_specs/*/ui/card -name "sg-compute-*-card.js"` returns 8; the brief's "12 spec cards" mention (echoed in FV2.9) means 4 specs (linux?) have no card. FV2.12 doesn't notice.

**Verdict:** ⚠ Has issues — sweep itself was thorough for the renamed scope, but methodology missed (a) parent dir, (b) dead script tags in `user/index.html`, (c) verification.

---

## Top 5 frontend issues across these 6 phases (severity-ordered)

1. **🔴 BLOCKING — `Pod__Manager` sidecar API key mismatch (FV2.7).** Control plane reads sidecar key from env `SG_COMPUTE__SIDECAR__API_KEY`. Dashboard holds per-node `host_api_key`. Per-node keys never traverse to the control plane, so unless the env var equals every node's key (impossible for nodes launched with random keys), Pods tab will return 401-driven `Sidecar__Client` exceptions in production. **Will break Pods tab end-to-end on first real deploy.** No test covers it. Either centralise sidecar API key (vault-sourced, BV2.9 PROPOSED), or have the dashboard pass the per-node key through control plane (requires header forwarding in `Routes__Compute__Pods`).

2. **🔴 BLOCKING — `user/index.html` references 3 deleted components (FV2.12).** `sg-compute-launch-modal`, `sg-compute-stack-detail`, `sg-compute-vault-activity` referenced as both `<script type="module" src=...>` and `<sg-compute-launch-modal>` element. Modules return 404; element renders as empty unknown-element; `/user/` page is broken. Pre-existing latent bug; FV2.12 cosmetic sweep had a clean opportunity to catch it and didn't.

3. **🟠 HIGH — FV2.10 missed flagship deliverable: arrow-key tab switching.** Brief explicitly required ←/→/Home/End on the nodes-view tablist. Zero hits in code for `ArrowLeft`/`ArrowRight`/`Home`/`End`. ARIA roles applied without the keyboard semantics they imply. Screen-reader users will be told "tab 1 of 6" but cannot use the standard keys to switch.

4. **🟠 HIGH — FV2.9 dropped `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` emitter migration.** Brief task 1.4 explicitly required dual-dispatch in `shared/settings-bus.js`. Done in card emitters; **NOT done in settings-bus**. Spec doc lists `sp-cli:spec.toggled` as RESERVED — ie wishful, not actual. Per-spec toggle UX never shipped.

5. **🟡 MEDIUM — FV2.11 silently dropped operator-IP-detection replacement.** Brief offered Option A (backend endpoint) or Option B (local heuristic) as required replacements. Dev chose neither and removed the field outright. Privacy goal achieved; UX regressed; backend ticket not filed. Should have been escalated, not absorbed.

**Honourable mentions:**
- FV2.7 silently dropped `/pods/{name}` and `/pods/{name}/stats` migration (brief listed them; only `list` and `logs` shipped).
- FV2.7 host status + pod stats remain cross-origin, contradicting brief's "Notes" section claim that only iframe ops would stay direct.
- FV2.10 contrast check sampled n=1 not n=5; `--text-3` 3.8:1 fails AA body and was punted.
- Spec doc `library/docs/specs/v0.2.0__ui-event-vocabulary.md` was published with already-stale paths (`sp-cli-stacks-pane.js` listed as emitter for `sp-cli:node.selected` but that file was deleted same day in FV2.11).
- FV2.12 retained `STATIC.type_id` alongside the new `spec_id` — no marker that `type_id` is deprecated.

---

## Cosmetic rename FV2.12 — verification checklist

| Check | Command | Expected | Actual | Status |
|-------|---------|----------|--------|--------|
| Tag/class residue | `grep -rn "sp-cli-" api_site/ --include="*.js" --include="*.html" --include="*.css"` | 0 | 0 | ✅ |
| `SpCli` class residue | `grep -rn "SpCli" api_site/` | 0 | 0 | ✅ |
| `customElements.define('sp-cli-...'` | `grep -rn "customElements.define.'sp-cli-" api_site/` | 0 | 0 | ✅ |
| `document.querySelector('sp-cli-...'` | `grep -rn "querySelector.'sp-cli-" api_site/` | 0 | 0 | ✅ |
| `document.createElement('sp-cli-...'` | `grep -rn "createElement.'sp-cli-" api_site/` | 0 | 0 | ✅ |
| Spec UI cards renamed | `find sg_compute_specs -name "sp-cli-*"` | 0 | 0 | ✅ |
| Spec UI cards have new name | `find sg_compute_specs -name "sg-compute-*-card.js" \| wc -l` | 8 | 8 | ✅ |
| Parent dir renamed | `find api_site/components -maxdepth 1 -name "sp-cli"` | 0 | 1 (`components/sp-cli/`) | ❌ |
| Imports use new parent | `grep -rn "components/sp-cli/" api_site/ \| wc -l` | 0 | 38 | ❌ |
| `_shared` family renamed | `ls components/sp-cli/_shared/` | all `sg-compute-*` | 9/10 (`sg-remote-browser` correctly retained) | ✅ |
| `<script>` src to extant files | `for f in admin/index.html user/index.html: each src points at extant file` | all valid | 3 dead in `user/index.html` (`sg-compute-launch-modal`, `sg-compute-stack-detail`, `sg-compute-vault-activity`) | ❌ |
| Element tags in HTML extant | `<sg-compute-X></sg-compute-X>` markup matches a registered customElement | all valid | 1 dead in `user/index.html:31` (`<sg-compute-launch-modal>`) | ❌ |
| Event names preserved (`sp-cli:`) | `grep -c "sp-cli:" api_site/` | > 0 (intentional) | 92 | ✅ |
| localStorage keys preserved (`sp-cli:`) | `grep -n "sp-cli:" shared/settings-bus.js shared/vault-bus.js` | preserved | preserved | ✅ |
| spec doc updated to reflect rename | `grep -n "sp-cli-" library/docs/specs/v0.2.0__ui-event-vocabulary.md` | should reference `sg-compute-` | references `sp-cli-stacks-pane.js` etc | ❌ |
| Snapshot tests pass | n/a | n/a | no snapshot tests exist | n/a |
| Manual smoke test every view | n/a | claim in debrief | no evidence | ❌ |

**Sweep verdict:** Mechanically thorough on the renamed scope (zero residue in tag/class names) but **methodology missed three classes of regression**: (1) the parent directory, (2) dead script tags pointing at non-existent components, (3) updating the same-week event-vocabulary spec doc to reflect the rename. Net: a follow-up "FV2.12.1" cleanup is justified before v0.3.
