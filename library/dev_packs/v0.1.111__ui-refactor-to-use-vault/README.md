# Provisioning UI — Rebase onto Tools + Vault Integration

**Brief:** v0.1.105 — Provisioning UI Rebase
**Status:** PROPOSED — ready for Sonnet pickup
**Target version:** v0.1.105
**Date drafted:** 2026-04-29
**Author:** Architect (Opus session)
**Audience:** Sonnet (implementation), Architect, DevOps
**Builds on:** v0.1.101 MVP brief (`team/comms/briefs/v0.1.101__mvp-of-admin-and-user-ui/`)

---

## What this brief is

A redesign of the Playwright provisioning UI that:

1. **Looks and feels like a cloud-provider console** (AWS as the structural reference, GCP-influenced spacing).
2. **Imports its building blocks directly from `https://dev.tools.sgraph.ai/`**, joining the SGraph component ecosystem instead of running a parallel one.
3. **Uses an SGraph vault as its persistent state layer** for everything beyond the current page session — preferences, cached active stacks, activity log, catalog overrides.
4. **Keeps two pages** — `/admin/` and `/user/` — but builds them from shared components and a shared vault. They are *lenses on the same data*, not permission tiers.

This is **not** an incremental polish of the current UI. It is a rebase. The brief specifies the next version end-to-end; the implementing Sonnet session is expected to pattern-match against the current code rather than work from a delta.

## What this brief is NOT

To prevent scope creep, here is what is explicitly out of scope:

- ❌ **Backend changes to `Fast_API__SP__CLI`.** No new endpoints, no new schemas, no service refactors. The vault story for MVP is *UI-only writer* — see doc 03.
- ❌ **Per-user authentication or authorisation.** Anyone with the vault key has full access. Auth is a follow-up brief.
- ❌ **Backend writing to the vault.** That is the immediate-next brief after this one lands.
- ❌ **VNC / SSM browser terminal / iframe embedding of running services.** Each is its own brief.
- ❌ **Replacing the FastAPI as the orchestrator.** It stays the source of truth for "what's running"; vault is for derived/cached state.
- ❌ **i18n / locale routing.** English only for now; the design leaves room.
- ❌ **Mobile layouts.** Desktop-first; responsive enough not to break.
- ❌ **A new build toolchain.** Native ES modules, no bundler, no React, no Lit.

## How to read this series

| # | Doc | Read when | Approx size |
|---|---|---|---|
| `00` | [`README.md`](README.md) *(this file)* | First — orientation | ~150 lines |
| `01` | [`visual-design.md`](01__visual-design.md) | When designing or building any UI surface | ~300 lines |
| `02` | [`component-architecture.md`](02__component-architecture.md) | When wiring components, naming files, picking imports | ~250 lines |
| `03` | [`vault-integration.md`](03__vault-integration.md) | When working on persistence, identity, or vault-backed state | ~200 lines |
| `04` | [`implementation-plan.md`](04__implementation-plan.md) | When picking the next PR to ship | ~200 lines |

Total ~1,100 lines. Read 00 + 01 once. Read 02–04 in the PR you're touching.

## Key decisions (made — do not relitigate)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Two separate pages: `/admin/` and `/user/`.** Not consolidated into one. | Different audiences, different defaults. Sharing components is enough; sharing the page is over-coupling. The lens-not-permission model means they can drift in copy and emphasis without contradiction. |
| 2 | **Tools is a hard dependency.** Imports come from `https://dev.tools.sgraph.ai/components/...` and `https://dev.tools.sgraph.ai/core/...`. | Matches what `sgraph.ai` already does. Version-pinned in URL. Verified CORS-enabled and serving 200 on the relevant paths. |
| 3 | **Custom Playwright top bar.** Not `<sg-site-header>` from Tools. | This is a console, not a marketing page. Top bar contains: brand mark, page title ("Provisioning Console"), region picker, vault picker rightmost. Specific to this product. |
| 4 | **Vault is the persistent state layer.** Anything that survives a page refresh, that's not a current-session detail, lives in vault — not localStorage, not Drive App Data, not anywhere else. | Single substrate. Same key opens it from browser, Lambda, or EC2 — that's the architecture. localStorage retained only for things that *have* to survive without a vault connection (the vault key and endpoint themselves). |
| 5 | **MVP is UI-only writer.** Backend is unchanged. The UI both reads from and writes to vault. | Smallest change that proves the pattern. Backend-as-vault-writer is the immediate-next brief; UI doesn't change when that lands. |
| 6 | **Admin and user are lenses, not permissions.** Same vault, same data, two default-views. | For MVP, anyone with the vault key has full access. When per-user identity arrives later, the lens metaphor extends — admin sees all users' stacks, user sees their own — without architectural change. |
| 7 | **Components extend `SgComponent` from Tools.** Three-file shape (`.js` + `.html` + `.css`). Shadow DOM. | The canonical SGraph pattern. The current UI's bespoke `attachShadow` boilerplate gets replaced. |
| 8 | **Visual reference: AWS console structure with GCP-influenced spacing.** | Operators recognise AWS patterns (table-of-resources, [Launch] top-right, status colour conventions, detail-on-row-click). GCP gives breathing room. AWS's density is a defect to avoid. |
| 9 | **Vault picker placement: top-bar rightmost, AWS-account-style.** Click → dropdown of recent vaults + connect/create/disconnect. | The vault is the equivalent of the AWS account in our model — it's the identity. Always-visible top-right is correct. |
| 10 | **Pages live at `/admin/` and `/user/` under existing `__api_site/`.** | No new path scheme. Existing URLs preserved. Internally, the implementations get rebuilt; from the operator's perspective the URLs they bookmarked still work. |
| 11 | **Page layout uses `<sg-layout>` from Tools** for resizable panes and tabbed panels. | The same component vault-peek and other tools use. Gives us pane resizing, drag-to-dock, tabbed file-viewers, serialisable layouts — for free. The admin page especially benefits (active stacks + activity + detail panel as resizable + tabbable). |
| 12 | **Connection requires two secrets, not one: vault key (read-or-write key, like a DB connection string) and access token (server-level credential needed to push writes).** Both stored in `localStorage` for one-click reconnect on next load. | Matches `<sg-vault-connect>`'s design. Vault key alone gives read-only access to the data; access token is required for writes. The brief consistently calls this out so operators understand they're providing two secrets, not one. |
| 13 | **A live "Vault activity" trace is visible on both pages**, showing reads and writes as they happen — file ID, path, bytes, latency. | Operators need to see when vault is being touched, especially during the MVP where vault operations are new. Implemented as `<sp-cli-vault-activity>` — listens for vault-bus events and renders a chronological log. |

## Layering rules (non-negotiable)

These extend the v0.1.101 brief's rules. If anything here contradicts the older brief, this one wins.

1. **All cross-component communication via DOM events.** No imports of one component's class from another. Events bubble + composed.
2. **Event naming: `{family}:{action}`.** `vault:connected`, `sg-vault-fetch:content-ready`, `sp-cli:stack-launch-requested`. Colon-separated. The product-specific family for this UI is `sp-cli:`.
3. **Tools imports are version-pinned URLs.** `https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js`. No `latest`, no aliases, no shortened paths.
4. **No fetch outside `<sg-api-client>`.** Already the rule; reinforced here. The vault adds a second class of allowed fetch — `<sg-vault-fetch>` and the `vault-client` core module — both come from Tools and are not re-implemented.
5. **No localStorage outside the vault-connect component and the api-client.** Keys namespaced `sp-cli:*` and `sg-vault:*`. No `sg_api_url` or other unprefixed keys.
6. **Components are dumb renderers.** Page controllers (`admin.js`, `user.js`) wire them.
7. **No synchronous `<script>` for component definitions.** Always `<script type="module">`.

## Acceptance for "this brief is done"

A reviewer should be able to confirm all of these:

1. `/admin/` and `/user/` both load against a fresh deployment with no console errors.
2. The top bar in both pages shows: brand mark, page title, region picker, vault picker.
3. Connecting to a vault for the first time prompts for a vault key + access token; subsequent loads pre-fill the connect form so reconnect is one click (see doc 03 for why MVP is one-click rather than silent).
4. After vault connection, the user page shows: type cards, my-active-stacks list. The admin page shows: the cross-team stacks table, type cards, activity log.
5. Launching a Linux stack from `/user/` shows the new wizard with **explicit checkpoint steps** (Created → Pending → Running → SSM ready → Ready), not a free-text log.
6. Closing the wizard at any time does not cancel the launch. The stack continues; the user can reopen its detail panel from the active list.
7. Clicking any stack row opens a detail panel with: full info (type, AMI, IP, allowed IP, instance ID, launch time, uptime, auto-stop in), the SSM connect command with a copy button, and stop/restart actions.
8. The activity log on the admin page persists across page refreshes (it's read from vault).
9. `grep -r "fetch(" sgraph_ai_service_playwright__api_site/` returns hits only in `<sg-api-client>` paths and the `vault-client` core module URLs (i.e. Tools-imported fetch is allowed).
10. `grep -r "localStorage" sgraph_ai_service_playwright__api_site/` returns hits only in vault-connect, api-client, and explicit `sp-cli:*`-prefixed keys.
11. Visually, both pages reference AWS console patterns (top bar, resource list, [Launch] CTA, detail panel, status dots) but with GCP-influenced spacing (~16-24px row padding, restrained accent use).
12. All components extend `SgComponent` (`grep "extends SgComponent"` finds every component class).
13. The vault picker prompts for **two secrets** — vault key and access token — and clearly labels each. Both are stored namespaced in localStorage under `sp-cli:vault:*` so subsequent page loads pre-fill the connect form.
14. A live **Vault activity** pane is visible on both pages, showing reads and writes against the vault as they happen — including action (read/write), path, file ID (short), bytes, latency. Operators can see at a glance whether vault is being touched.
15. Page layout uses `<sg-layout>` from Tools — operators can resize panes (drag the splitter) and the activity pane lives as a separate tab they can collapse or expand.

If any fails, the brief is not done.

## Effort estimate

Roughly 8–11 dev-days for one developer, more if the dev is unfamiliar with `SgComponent` and `<sg-layout>`:

- 1d — Playwright-side scaffolding: top bar, region picker, route flow, tools-imports wiring
- 1.5d — Vault integration scaffold: connect with two secrets (vault key + access token), key persistence, event bus + trace-event dispatch, `<sp-cli-vault-activity>` pane, "vault not connected" state, "read-only" banner
- 1.5–2d — sg-layout adoption: page shells use `<sg-layout>`, pane-wrapper components, layout-state persistence
- 1.5d — Resource list + detail panel
- 1d — Launch wizard with checkpoint state machine
- 1d — Type cards + user-page active strip + admin-page activity log (the application log, not the vault trace)
- 1d — Polish: empty states, loading states, error states, AWS-style status dots, two-secret form copy
- 1d — Promotion of generic components to Tools (api-client, poll, toast-host) — see doc 02
- 0.5d — Vault writes wired into preferences, active-stacks-cache, activity-log
- 0.5d — Browser-runnable manual smoke tests + demo run-through

The largest risks are `SgComponent` and `<sg-layout>` familiarity — if either is the developer's first time, add 1d each. The smallest risk is the vault — `<sg-vault-connect>` does the heavy lifting; we're just composing it.

## What ships after this brief

Roadmap, in order of likely priority:

1. **Backend-as-vault-writer.** `Fast_API__SP__CLI` gets a vault-key env var and writes to the same paths the UI writes today. UI doesn't change. Operators get a single source of truth.
2. **OpenSearch tile flips live.** Catalog config change + route mount.
3. **VNC integration.** Depends on `sp vnc` slice landing.
4. **SSM browser terminal.** `Routes__Ssm` + `<sp-cli-ssm-terminal>`.
5. **Per-user identity.** Google OAuth → vault key derivation per user → user permissions in vault.

Each is its own focused brief.
