# 04 — Implementation Plan

**Status:** PROPOSED
**Read after:** all of `00`–`03`
**Audience:** Sonnet planning the PR sequence

---

## What this doc gives you

The PR sequence in dependency order, files touched per PR, acceptance per PR, and the sequencing rules for working on more than one PR in parallel.

This is the implementation map. Doc 01 describes what to build; doc 02 describes how the components compose; doc 03 describes the vault layer; this doc says **what order to ship in**.

## Pre-flight (before any PR)

```bash
# Ensure you're on latest dev
git fetch origin dev && git merge origin/dev
git checkout -b claude/provisioning-ui-rebase-{session-id}

# Verify Tools imports are reachable from your dev machine
for url in \
  "components/tokens/v1/v1.0/v1.0.0/sg-tokens.css" \
  "components/base/v1/v1.0/v1.0.0/sg-component.js" \
  "core/vault-client/v1/v1.2/v1.2.2/sg-vault-client.js" \
  "components/vault/sg-vault-connect/v0/v0.1/v0.1.3/sg-vault-connect.js" \
; do
  curl -s -o /dev/null -w "%{http_code} %s\n" "https://dev.tools.sgraph.ai/${url}"
done
# Expected: all 200
```

If any returns 404, see doc 02's "Verifying versions before use" section before proceeding.

Read these existing files before designing your PR sequence — they're the patterns you're rebasing onto:

| File | Read for |
|---|---|
| `library/catalogue/02__cli-packages.md` | Current state of the SP-CLI surface |
| `team/roles/librarian/reality/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md` | Slice 13 reality — what the v0.1.101 MVP UI shipped |
| `team/claude/debriefs/2026-04-29__v0.1.101__mvp-admin-user-ui.md` | Debrief from the MVP UI session — what the next session learned |
| The current `sgraph_ai_service_playwright__api_site/` tree | What you'll be replacing |

---

## The PR sequence

Six PRs, sequenced in strict dependency order. Each is independently shippable and reviewable. The whole sequence runs **7–10 dev-days for one developer**.

```
PR-1  Tools-imports scaffold             ◀── start here
  │
PR-2  Vault layer                        ◀── needs PR-1's SgComponent imports
  │
PR-3  Top bar + page shells              ◀── needs PR-1, PR-2
  │
PR-4  Stack list + detail panel          ◀── needs PR-3
  │
PR-5  Launch wizard + type cards         ◀── needs PR-3, PR-4 (for refresh)
  │
PR-6  Promote generic components         ◀── parallel with PR-3 onwards
        to Tools, switch imports
```

PR-6 can be done in parallel with PR-3+ once Tools deploys land — it's a Tools-side PR followed by a Playwright-side import swap.

---

## PR-1 — Tools-imports scaffold

**Goal:** establish the new file layout and prove that Tools imports work end-to-end. Nothing visible to operators yet.

### Files touched

- `sgraph_ai_service_playwright__api_site/components/sp-cli/` — create directory tree (just the empty subdirs from doc 02's file tree, with empty `.js`/`.html`/`.css` placeholders for `sp-cli-top-bar`)
- `sgraph_ai_service_playwright__api_site/shared/vault-bus.js` — stub (just exports declared, no implementation; PR-2 fills it)
- `sgraph_ai_service_playwright__api_site/admin/index.html` — minimal page that loads `sg-component.js` from Tools and renders a single `<sp-cli-top-bar>` to prove the pattern works
- `sgraph_ai_service_playwright__api_site/user/index.html` — same minimal page

### Files created

- `components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/sp-cli-top-bar.js` — full implementation per doc 02's worked example
- `components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/sp-cli-top-bar.html`
- `components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/sp-cli-top-bar.css`

### Acceptance

- Open `/admin/` in a browser → top bar renders with brand mark, "Admin Dashboard" title, region picker showing `eu-west-2`, an empty slot where the vault picker will go.
- Open `/user/` → same top bar, "Provisioning Console" title.
- Browser DevTools Network tab shows requests to `https://dev.tools.sgraph.ai/components/base/...` and `https://dev.tools.sgraph.ai/components/tokens/...` returning 200.
- `grep "extends SgComponent" components/sp-cli/sp-cli-top-bar/v0/v0.1/v0.1.0/*.js` finds one match.
- No console errors.
- Existing pages (the old `/admin/` and `/user/` if they still resolve) are not broken — but we're replacing them, so the old `admin/admin.js`, `user/user.js`, etc. can stay untouched until later PRs delete them.

### Effort

**0.5–1 day.** Most of this is getting comfortable with `SgComponent`'s three-file pattern and confirming the import URLs work. Once the top-bar component renders correctly, the rest of the brief follows the same pattern.

---

## PR-2 — Vault layer + activity tracer

**Goal:** connect to a vault (with both vault key and access token), persist the connection across reloads, expose helpers for path-based reads/writes, and render a live trace of every vault interaction. Page is still mostly empty; the vault picker and activity pane are the visible features.

### Files touched

- `sgraph_ai_service_playwright__api_site/shared/vault-bus.js` — full implementation per doc 03 (including `sp-cli:vault-bus:*` trace event dispatch)
- `sgraph_ai_service_playwright__api_site/admin/admin.js` — bootstrap: import vault-bus, listen for `vault:connected`, log to console
- `sgraph_ai_service_playwright__api_site/user/user.js` — same
- `admin/index.html` and `user/index.html` — add `<sp-cli-vault-picker>` into the top bar's slot, add a temporary container for `<sp-cli-vault-activity>` (PR-3 wraps this in `<sg-layout>`)

### Files created

- `components/sp-cli/sp-cli-vault-picker/v0/v0.1/v0.1.0/sp-cli-vault-picker.{js,html,css}` — the two-secret connect dropdown from doc 01, embedding `<sg-vault-connect>` from Tools, with explicit help text per field, and the read-only banner triggering for missing access token
- `components/sp-cli/sp-cli-vault-activity/v0/v0.1/v0.1.0/sp-cli-vault-activity.{js,html,css}` — the live trace pane per doc 03

### Tests / verification

- Open `/admin/` with a fresh browser profile (no localStorage). Top-bar vault picker shows "Connect a vault →".
- Click → connect form appears with TWO labelled fields: "Vault key" and "Access token". Both have help text.
- Paste a known test vault key + access token → click Connect.
- `vault:connected` fires. `sp-cli:vault-bus:*` events appear in the activity pane (read-started → read-completed for the initial preferences/cache reads).
- Reload the page. Vault picker shows the connect form pre-filled with both fields — one click reconnects without re-pasting.
- Click vault picker → dropdown shows current vault stats (file count from `session.treeModel.getStats()`).
- Connect with no access token → vault picker shows "Read-only" banner. Trigger a write (e.g. via dev console: `import('../shared/vault-bus.js').then(m => m.vaultWriteJson('test.json', {a:1}))`) → write throws "vault is read-only" and the activity pane shows a `write-error` entry with `reason: 'read-only'`.
- Click Disconnect → returns to "Connect a vault" state. localStorage clears `sp-cli:vault:last-read-key` AND `sp-cli:vault:last-access-token`; `last-vault-id` and `last-endpoint` stay for "recents".
- `grep "localStorage" sgraph_ai_service_playwright__api_site/shared/vault-bus.js` shows only `sp-cli:vault:*` keys (`last-vault-id`, `last-read-key`, `last-access-token`, `last-endpoint`, `recents`).

### Acceptance

A reviewer can connect (with both secrets), disconnect, switch vaults, reload, and watch the activity pane update live. The two-secret separation is visible in the form. The read-only banner shows when access token is missing. PR-3 fills the rest with content.

### Effort

**1.5 days.** The vault primitives are well-tested in Tools; the work is in `vault-bus.js`'s persistence + trace dispatch, the two-secret picker UX (with help text and the read-only banner), and `<sp-cli-vault-activity>` (~200 lines of SgComponent listening for events).

---

## PR-3 — sg-layout shells + region picker + page chrome

**Goal:** the page layouts use `<sg-layout>` for resizable panes and tabs. The vault gate works. Empty states are in place. Still no actual stack data.

### Files touched

- `admin/index.html` — full page shell per doc 01: top bar + sg-layout root with the admin layout JSON
- `admin/admin.js` — wire vault-bus + sg-layout setLayout, render the "vault not connected" overlay
- `admin/admin.css` — admin-specific layout (mostly minimal — sg-layout owns the panel chrome)
- `user/index.html` — full page shell with the simpler user layout
- `user/user.js` — same wiring as admin
- `user/user.css` — user-specific layout
- `index.html` (root) — landing page with `[Admin]` and `[Provision]` links, refreshed visual style

### Files created

- `components/sp-cli/sp-cli-region-picker/v0/v0.1/v0.1.0/sp-cli-region-picker.{js,html,css}`
- `components/sp-cli/sp-cli-stacks-pane/v0/v0.1/v0.1.0/sp-cli-stacks-pane.{js,html,css}` — admin-page Stacks tab wrapper (still empty for now)
- `components/sp-cli/sp-cli-catalog-pane/v0/v0.1/v0.1.0/sp-cli-catalog-pane.{js,html,css}` — admin Catalog tab placeholder (says "Coming soon — admins can edit catalog overrides directly via vault tools for now")
- `components/sp-cli/sp-cli-activity-pane/v0/v0.1/v0.1.0/sp-cli-activity-pane.{js,html,css}` — admin Activity Log tab wrapper (still empty for now; populated in PR-5)
- `components/sp-cli/sp-cli-user-pane/v0/v0.1/v0.1.0/sp-cli-user-pane.{js,html,css}` — user-page main tab wrapper

### Acceptance

- `/admin/` connected: shows top bar (with vault + region picker), the row layout from doc 01 — left: tabbed stack with Stacks/Catalog/Activity Log, right: Vault Activity. Resize splitter works. Tab switching works.
- `/admin/` not connected: page is dimmed, single centred card "Connect a vault to use this console" with `[Connect →]` button.
- `/user/` connected: shows top bar, single-pane main with type cards and active strip, vault activity collapsed by default with a `[Vault activity ▶]` toggle.
- All section headers, copy, and visual structure match the layouts in doc 01.
- Drag the splitter on `/admin/` to a non-default size → reload → splitter at the new size (sg-layout preserves state).
- Visual: pages use `sg-tokens.css` colours throughout (no bespoke palette).
- `grep -r "var(--color-" sgraph_ai_service_playwright__api_site/` returns no hits.

### Effort

**1.5–2 days.** sg-layout adoption is the new bit — about half a day to learn the API (read `sg-layout.js` lines 1-200 plus `vault-peek/ui/ui-layout.js` as a reference) and wire the layout JSON correctly. The pane wrapper components are thin (just composition shells). The rest is layout CSS and empty states.

---

## PR-4 — Stack list + detail panel

**Goal:** display real stack data. Read from FastAPI. Cache to vault. Detail panel slides in on row click. This is the largest PR; consider splitting if time allows.

### Files created

- `components/sp-cli/sp-cli-stack-table/v0/v0.1/v0.1.0/sp-cli-stack-table.{js,html,css}` — admin-page table
- `components/sp-cli/sp-cli-stack-card/v0/v0.1/v0.1.0/sp-cli-stack-card.{js,html,css}` — user-page active-strip row
- `components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/sp-cli-stack-detail.{js,html,css}` — slide-in panel
- `components/sp-cli/sp-cli-confirm-modal/v0/v0.1/v0.1.0/sp-cli-confirm-modal.{js,html,css}` — Stop confirmation
- `shared/api-client.js` — if not already promoted, the existing api-client (we may promote in PR-6 or use the existing one for now)

### Files touched

- `admin/admin.js` — wire stack table, refresh cycle, click → detail
- `user/user.js` — wire stack-card list (different render but same data flow)
- `admin/index.html`, `user/index.html` — slot in the new components

### Behaviours wired

- On `vault:connected`, start the cache-then-fresh refresh cycle from doc 03.
- Click a row → detail panel opens, fetches `GET /{type}/stack/{name}` for full info, populates panel.
- Click `[Stop]` (in row, in detail panel, in user card) → `<sp-cli-confirm-modal>` opens with stack-specific message → confirm fires `DELETE /{type}/stack/{name}` → toast on result → refresh.
- Status dot colours per doc 01's status table.
- Detail panel's collapsibles (Resource details, Recent activity) work.
- SSM command copy button works.
- Empty states render correctly when no stacks exist.
- "Stale" indicator appears when fresh fetch fails.

### Acceptance

- Launch a real linux stack via CLI (`sp linux create --wait`). Open `/admin/` → it appears in the table within 15s.
- Click the row → detail panel slides in with all fields populated. SSM command shown. Click copy → command in clipboard.
- Click `[Stop]` → confirmation modal → confirm → stack disappears from table within one refresh cycle.
- Reload the page mid-refresh — cached stacks render instantly from vault.
- Disconnect the vault — table clears, page goes back to "Connect" state.
- Reconnect → table re-populates from cache, then fresh.

### Effort

**2 days.** This is the biggest PR — three new components, three new behaviours (refresh, detail, stop), polish. Could split into PR-4a (table + cards) and PR-4b (detail panel + confirm modal) if needed.

---

## PR-5 — Launch wizard + type cards + activity log

**Goal:** the launch flow works end-to-end with explicit checkpoint progress, and the admin's recent-activity log persists.

### Files created

- `components/sp-cli/sp-cli-type-card/v0/v0.1/v0.1.0/sp-cli-type-card.{js,html,css}` — the launch tile
- `components/sp-cli/sp-cli-launch-wizard/v0/v0.1/v0.1.0/sp-cli-launch-wizard.{js,html,css}` — multi-state wizard from doc 01
- `components/sp-cli/sp-cli-activity-log/v0/v0.1/v0.1.0/sp-cli-activity-log.{js,html,css}` — admin-only

### Files touched

- `admin/admin.js`, `user/user.js` — wire type cards (both pages) and activity log (admin only)
- `shared/poll.js` — promote or use the existing one for the wizard's poll loop

### Behaviours wired

- Type cards rendered from merged catalog (FastAPI + vault overrides per doc 03).
- Click `[Launch]` on a type card → wizard opens with form pre-filled from preferences.
- Submit → POST → wizard transitions to progress with checkpoint state machine.
- Health polling drives checkpoint progression — first reached state ticks ✅, current state shows ◐ spinner.
- Closing the wizard at any time does not cancel the launch (verified by checking `GET /catalog/stacks` after close).
- On READY → wizard shows success view with SSM command + Open Details + Done buttons.
- On error → wizard shows error step in red with `[Retry]` and `[Cancel and stop]` buttons.
- Every action appends to vault `sp-cli/activity-log.json`.
- Activity log component reads vault on `vault:connected` and on `sp-cli:activity-updated`.

### Acceptance

- Launch a Linux stack via the wizard. Watch the checkpoint state machine progress through Created → Pending → Running → SSM ready → Ready in real time.
- Close the wizard mid-launch. Reopen via the active strip → see the stack still progressing. SSM command available once ready.
- Failed launch (force by stopping the FastAPI mid-launch) → wizard shows error, retry works.
- `/admin/` shows the launch and ready transitions in the activity log.
- `/admin/` reload — activity log persists across refresh (read from vault).

### Effort

**1.5–2 days.** Wizard's checkpoint logic is the trickiest part — drive it from health responses, handle skip cases (elastic skips the SSM checkpoint), interpolate the bar against `expected_boot_seconds`.

---

## PR-6 — Promote generics to Tools

**Goal:** move the genuinely generic components (`api-client`, `poll`, `sg-toast-host`, `sg-auth-panel`) into the Tools repo. Switch Playwright imports to Tools URLs. **Can run in parallel with PR-3 onwards** once the Tools-side merges have landed.

### Two-repo workflow

**Step 1: Tools-side PR.** In `SGraph-AI__Tools`:
- Create `sgraph_ai_tools__static/components/tool-api/sg-api-client/v0/v0.1/v0.1.0/sg-api-client.{js,html,css}` — port from Playwright's local copy. Extend `SgComponent`. Add module-header JSDoc per Tools convention.
- Create `sgraph_ai_tools__static/core/poll/v0/v0.1/v0.1.0/sg-poll.js` — port from `shared/poll.js` (no UI; module-only).
- Create `sgraph_ai_tools__static/components/feedback/sg-toast-host/v0/v0.1/v0.1.0/sg-toast-host.{js,html,css}` — port.
- Create `sgraph_ai_tools__static/components/auth/sg-api-key-panel/v0/v0.1/v0.1.0/sg-api-key-panel.{js,html,css}` — port from `sg-auth-panel`, generalise with a `storage-prefix` attribute (defaulting to `sg`).
- Open Tools PR, merge, deploy. Verify URLs respond 200.

**Step 2: Playwright-side PR.** In `SGraph-AI__Service__Playwright`:
- In `admin/admin.js`, `user/user.js`, and any other consumer, replace `import {...} from '../shared/api-client.js'` with `import {...} from 'https://dev.tools.sgraph.ai/components/tool-api/sg-api-client/v0/v0.1/v0.1.0/sg-api-client.js'`.
- Same for `poll.js` → `core/poll/v0/v0.1/v0.1.0/sg-poll.js`.
- Same for `<sg-toast-host>` and the API key panel.
- Delete the local copies in `shared/`.
- Verify all functionality still works.

### Acceptance

- `grep -r "import .* from '../shared/api-client.js'"` returns zero hits in Playwright.
- `grep -r "import .* from 'https://dev.tools.sgraph.ai/"` returns multiple hits.
- `/admin/` and `/user/` work identically to before the import switch.
- Tools deployment tags include the new component versions.

### Effort

**1 day** — half on each side. Mechanical work, low risk, but requires Tools merge + deploy first.

### Fallback if Tools-side stalls

Keep the local copies in `shared/`, mark with `// TODO: promote to Tools (PR-6)` comments, ship the Playwright PRs without the import switch. The promotion can land later as a focused follow-up brief.

---

## What about the existing /admin/ and /user/ files?

The old `admin/admin.js`, `admin/admin.css`, `admin/index.html`, `user/user.js`, `user/user.css`, `user/index.html` are **rewritten in place**. PR-3 is where the rewrite happens — `admin/index.html` is replaced with the new shell, etc. The file paths stay the same; the content is new.

The shared root files (`app.js`, `cookie.js`, `health.js`, `storage.js`, `style.css`) — these are vestiges of the original v0.1.x EC2 launcher. **Delete them in PR-3.** They serve no purpose in the new architecture.

The existing root `index.html` becomes a small landing page in PR-3 with `[Admin]` and `[Provision]` buttons styled with `sg-tokens.css`.

The existing `shared/components/sg-*.js` files (sg-api-client, sg-auth-panel, etc.) — **delete in PR-6** when their Tools-side equivalents are imported. Until then they're vestigial but harmless.

---

## Sequencing across two developers

If Sonnet wants to parallelise:

| Track | PRs |
|---|---|
| **Track A** (foundations) | PR-1 → PR-2 → PR-3 |
| **Track B** (Tools-side promotion) | PR-6 — can start immediately |
| **Track C** (features, after Track A finishes) | PR-4 → PR-5 |

Track A is strict-sequential. Track B is parallel — it doesn't touch Playwright UI files until the import-swap step, which is gated on the Tools deploy. Track C depends on Track A.

A two-developer team finishes in ~5 elapsed days. A one-developer team in 7-10.

---

## What's NOT in this brief's PRs

Documented here so reviewers don't ask:

- ❌ The admin "Catalog editor" UI to edit `sp-cli/catalog-overrides.json` interactively. The vault file exists and is merged into the catalog; editing it is operator-via-vault-tools for now.
- ❌ The activity log "jump to stack" interaction. The events fire (`sp-cli:activity-row-clicked`); wiring it to open the detail panel is a polish item.
- ❌ Sortable columns on the admin stack table. Static order for MVP.
- ❌ Multi-region support beyond the picker chrome. Single region.
- ❌ Bulk actions (Stop All, Multi-select). Single-row only.
- ❌ Search across stacks. Filter dropdowns work; free-text search is polish.
- ❌ Real-time updates (WebSockets). Polling.
- ❌ Tests beyond manual smoke. Automated test harness is its own brief.
- ❌ Backend changes to `Fast_API__SP__CLI`. Per the README — this is UI-only.

---

## Final acceptance — across the full brief

When all 6 PRs are merged, an operator should be able to:

1. Open `/user/` on a fresh browser profile.
2. Be prompted to connect a vault.
3. Connect a vault. The page populates with type cards.
4. Click `[Launch]` on Linux. The wizard opens. The form is pre-filled from vault preferences.
5. Submit. Watch the checkpoint state machine show real progress against real health checks.
6. Close the wizard halfway. The active strip shows the in-progress launch.
7. Wait for it to reach Ready. Click `[Details]` on the active strip. SSM command available; copy it.
8. Switch to `/admin/`. See the same stack in the table. See the launch in the activity log.
9. Click the stack row. Detail panel opens. Click `[Stop stack]`. Confirm. Stack disappears.
10. Reload the page. Stacks list (now empty) renders instantly from vault cache. Activity log persists.
11. Disconnect the vault. Page goes back to "Connect a vault" prompt.
12. Reconnect. Everything restores.

If any step fails, the brief is not done.
