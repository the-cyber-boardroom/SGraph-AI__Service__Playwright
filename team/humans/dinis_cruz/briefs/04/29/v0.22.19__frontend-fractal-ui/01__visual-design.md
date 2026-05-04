# 01 — Visual Design

**Status:** PROPOSED
**Read after:** `00__README__frontend-fractal-ui.md`
**Read alongside:** `02__component-architecture.md` when implementing

---

## What this doc gives you

The full visual design for the rebuilt admin dashboard. Top-level layout, the four main views (Compute / Storage / Settings / Diagnostics), the per-type instance detail views, the launch-as-tab flow, the right info column. Concrete enough that you can build the HTML/CSS without a design review round-trip.

## The reference: cloud-provider consoles + IDE-style multi-pane workflow

The previous brief established **AWS console** as the structural reference for the admin surface. This brief extends that with **IDE-style multi-pane workflow** — VS Code, JetBrains, Figma — where:

- The left rail navigates between major modes (Files / Search / Git / Debug, in IDE terms; Compute / Storage / Settings / Diagnostics, in ours)
- The main area is a tabbed work surface that holds whatever you're currently doing
- The right rail is persistent system context (problems, terminal, debug, etc., in IDE terms; events log, vault status, sessions, cost, in ours)
- **Nothing happens in modals.** Everything happens in panels.

This pattern is already familiar to operators from their everyday tools.

## Top-level layout

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ┃SGraph┃  Provisioning Console            eu-west-2 ▾   🗝 clear-twig-0823 ▾         │
├────┬─────────────────────────────────────────────────────────────────┬───────────────┤
│    │                                                                 │               │
│ 🖥 │                                                                 │  Events Log   │
│Comp│                                                                 │  ─────        │
│    │                                                                 │  → vault:c…   │
│ 💾 │                                                                 │  → sp-cli:s…  │
│Stor│              MAIN COLUMN                                        │  → core:plu…  │
│    │              (Compute view rendered here by default)            │               │
│ ⚙  │                                                                 ├───────────────┤
│Set │                                                                 │ Vault Status  │
│    │                                                                 │ Connected     │
│ 🔧 │                                                                 │ 12 KB · 4 fl  │
│Diag│                                                                 │               │
│    │                                                                 ├───────────────┤
│    │                                                                 │ Active Sess.  │
│    │                                                                 │ • dinis  3h   │
│    │                                                                 │ • partner 1h  │
│    │                                                                 │               │
│    │                                                                 ├───────────────┤
│    │                                                                 │ Cost Tracker  │
│    │                                                                 │ Today: $1.42  │
│    │                                                                 │ (placeholder) │
└────┴─────────────────────────────────────────────────────────────────┴───────────────┘
   ↑               ↑                                                       ↑
   Left Nav        Main column (tabbed sg-layout)                          Right Info
   ~64px wide      flexible                                                ~280px wide
```

Implemented as a single `<sg-layout>` at the page root with this JSON:

```javascript
{
    type: 'row', sizes: [0.07, 0.78, 0.15],
    children: [
        { type: 'stack', tabs: [{ tag: 'sp-cli-left-nav', title: 'Nav', locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-compute-view', title: 'Compute', locked: true }] },  // default; replaced when nav selection changes
        {
            type: 'column', sizes: [0.30, 0.20, 0.20, 0.30],
            children: [
                { type: 'stack', tabs: [{ tag: 'sp-cli-events-log',     title: 'Events Log',     locked: true }] },
                { type: 'stack', tabs: [{ tag: 'sp-cli-vault-status',   title: 'Vault Status',   locked: true }] },
                { type: 'stack', tabs: [{ tag: 'sp-cli-active-sessions', title: 'Active Sessions', locked: true }] },
                { type: 'stack', tabs: [{ tag: 'sp-cli-cost-tracker',   title: 'Cost Tracker',   locked: true }] },
            ],
        },
    ],
}
```

The middle column's content **swaps** based on Left Nav selection — the Left Nav fires `sp-cli:nav.selected`, the page controller listens and replaces the main-column tab.

## Left Nav

A vertical icon-rail. ~64px wide. Each item is icon + small label.

```
┌────┐
│    │
│ 🖥 │  ← Compute  (selected — accent border)
│Comp│
│    │
│ 💾 │  ← Storage
│Stor│
│    │
│ ⚙  │  ← Settings
│Set │
│    │
│ 🔧 │  ← Diagnostics
│Diag│
│    │
└────┘
```

Selected item: solid teal left border + filled icon background. Hover: slight bg highlight. Click → fires `sp-cli:nav.selected { view: 'compute' | 'storage' | 'settings' | 'diagnostics' }`.

## Main column — Compute view (default)

The Compute view is the most complex one. Itself a row sg-layout:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─[ Compute ]──────────────────────────────────────────────────────────┐    │
│ │                                                                       │    │
│ │ Launcher                                                              │    │
│ │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │    │
│ │ │ 🐧     │ │ 🐳     │ │ 🔍     │ │ 🖥     │ │ 🌐     │ │ 📊     │    │    │
│ │ │ Linux  │ │ Docker │ │Elastic │ │ VNC    │ │ Neko   │ │OpenSrc │    │    │
│ │ │stable  │ │stable  │ │stable  │ │stable  │ │experim │ │ soon   │    │    │
│ │ │ ~60s   │ │ ~600s  │ │ ~90s   │ │ ~90s   │ │  ~60s  │ │  --    │    │    │
│ │ │[Launch]│ │[Launch]│ │[Launch]│ │[Launch]│ │[Launch]│ │ disab. │    │    │
│ │ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │    │
│ │                                                                       │    │
│ │ ─────────────────────────────────────────────────────────────         │    │
│ │                                                                       │    │
│ │ Active Stacks                                          🔄 [Refresh]   │    │
│ │ ┌────┬────────────────┬────────┬─────────────┬─────┬────────┐         │    │
│ │ │    │ Name           │ State  │ Public IP   │ Up  │        │         │    │
│ │ ├────┼────────────────┼────────┼─────────────┼─────┼────────┤         │    │
│ │ │ 🐧 │ linux-quiet-…  │●Ready  │18.132.60.220│ 4m  │  ⋯     │         │    │
│ │ │ 🐳 │ docker-bold-…  │◐Boot   │   —         │ 32s │  ⋯     │         │    │
│ │ │ 🔍 │ elastic-loud-… │●Ready  │3.10.42.118  │ 12m │  ⋯     │         │    │
│ │ │ 🖥 │ vnc-sharp-…    │●Ready  │13.43.123.91 │ 47m │  ⋯     │         │    │
│ │ └────┴────────────────┴────────┴─────────────┴─────┴────────┘         │    │
│ └───────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Compute view layout JSON:**

```javascript
{
    type: 'column', sizes: [0.35, 0.65],
    children: [
        { type: 'stack', tabs: [{ tag: 'sp-cli-launcher-pane', title: 'Launcher', locked: true }] },
        { type: 'stack', tabs: [{ tag: 'sp-cli-stacks-pane', title: 'Active Stacks', locked: true }] },
        // Additional tabs added dynamically: launch panels, instance detail panels (see below)
    ],
}
```

The Launcher pane reads from `GET /catalog/types`, filters by feature-toggle settings, renders one card per enabled plugin. Card shows: type icon, display name, stability badge ("stable"/"experimental"), expected boot time, **[Launch] button**.

The Active Stacks pane reads from `GET /catalog/stacks`, renders the table. Same shape as today's `<sp-cli-stacks-pane>`.

## The launch flow — as a tab, NOT a modal

This is the single biggest behaviour change. **No more modal dialog popping over everything.**

### Before (current)

```
User clicks [Launch] on a type card →
modal pops up centered →
backdrop dims the page →
form rendered in modal →
submit → modal closes → stack appears in list
```

### After (this brief)

```
User clicks [Launch] on a type card →
new tab opens in the Compute view's bottom sg-layout stack →
tab title: "Launching Linux"  →
form rendered as a normal panel inside the tab →
submit → tab closes (or stays open if the user wants to launch another) → stack appears in list
```

Visual:

```
┌─[ Active Stacks │ 🔍 Launching Elastic × ]──────────────────────────┐
│                                                                      │
│  Launching Elastic + Kibana                                          │
│  ─────────────────────────                                           │
│                                                                      │
│   Stack name        [auto-generated if blank        ]                │
│   Region            [eu-west-2                      ▾]               │
│   Instance type     [t3.medium                      ▾]               │
│   Auto-stop after   [4 hours                        ▾]               │
│                                                                      │
│   ▾ Advanced (collapsed)                                             │
│                                                                      │
│   ─────────────────────────────────────                              │
│                                       [Cancel]  [Launch →]           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

After clicking [Launch →]:

- Tab title changes to "Launching Elastic — submitting…"
- Form fields disabled
- Spinner shown
- On success: tab title changes to "Launched ✓ elastic-loud-noether"; tab can be closed by the user, OR auto-closes after 2 seconds
- On error: tab title shows "Launch failed"; error rendered in the panel; [Retry] button

The tab **never auto-modal-blocks** the rest of the UI. While launching, the operator can switch to other tabs, click on existing stacks, etc.

**Component:** `<sp-cli-launch-panel>` (renamed from the existing `<sp-cli-launch-modal>`). Wrapped to be sg-layout-hosted instead of position-fixed. ~80% of the existing logic preserved; the framing changes.

### Confirmations: inline, not modal

Stop / delete confirmations follow the **already-existing** pattern in `<sp-cli-stack-detail>` — a row appears within the panel asking "Stop linux-quiet-fermi? [Cancel] [Confirm]". No modal overlay.

## Per-type instance detail views

Click a row in Active Stacks → a new tab opens in the Compute view's bottom sg-layout stack. The tab tag is **type-specific**: `sp-cli-linux-detail`, `sp-cli-docker-detail`, `sp-cli-elastic-detail`, `sp-cli-vnc-detail`, etc.

Each detail view is itself an sg-layout, designed for that compute type's centre of gravity.

### Linux detail

Simple — Linux instances are mostly used for SSM access, so the view is:

```
┌─[ Linux: linux-quiet-fermi × ]────────────────────────────────────────┐
│                                                                        │
│  ┌──────────────┐ ●Ready · 4m 32s                                      │
│  │ ╔══════════╗ │ Type: t3.medium · eu-west-2                          │
│  │ ║   🐧     ║ │ Launched: 2026-04-29 01:38:14                        │
│  │ ╚══════════╝ │ Auto-stops in: 3h 55m                                │
│  └──────────────┘                                                      │
│                                                                        │
│  ─── Connect via SSM ─────────────────────────                         │
│  ┌────────────────────────────────────────────────┐                    │
│  │ aws ssm start-session --target i-0a1b2c3d…    │                    │
│  └────────────────────────────────────────────────┘                    │
│  [📋 Copy command]                                                      │
│                                                                        │
│  ─── Network ─────────────────────────────────                         │
│  Public IP: 18.132.60.220                                              │
│  Allowed: 82.46.x.x                                                    │
│  SG: sg-0a1b…                                                          │
│                                                                        │
│  ─── Resource details ▾ (collapsed) ──                                 │
│                                                                        │
│  ─── Recent activity ▾ (collapsed) ──                                  │
│                                                                        │
│  ─────────────────────────────────────                                 │
│  [Stop]  [Restart]  [Resize]                                           │
└────────────────────────────────────────────────────────────────────────┘
```

Composition: `<sp-cli-stack-header>` + `<sp-cli-ssm-command>` + `<sp-cli-network-info>` + `<sp-cli-resource-details>` (collapsible) + `<sp-cli-recent-activity>` (collapsible) + `<sp-cli-stop-button>`. All shared components from `_shared/`.

### Elastic detail

Elastic adds a **Kibana access pane** on the right — either iframe direct (if the deployment allows) or via `<sg-remote-browser>`:

```
┌─[ Elastic: elastic-loud-noether × ]──────────────────────────────────────────────┐
│                                                                                   │
│  ┌─[ Info ]──────────────────┐  ┌─[ Kibana ]──────────────────────────────────┐  │
│  │                           │  │                                              │  │
│  │ ●Ready · 12m              │  │ [Kibana iframe or sg-remote-browser]         │  │
│  │ t3.medium · eu-west-2     │  │                                              │  │
│  │ Launched: …               │  │                                              │  │
│  │ Auto-stops: 47m           │  │                                              │  │
│  │                           │  │                                              │  │
│  │ Endpoints:                │  │                                              │  │
│  │   Kibana 5601 [Open]      │  │                                              │  │
│  │   ES 9200    [Open]       │  │                                              │  │
│  │                           │  │                                              │  │
│  │ Containers:               │  │                                              │  │
│  │   elasticsearch ●         │  │                                              │  │
│  │   kibana        ●         │  │                                              │  │
│  │                           │  │                                              │  │
│  │ ─── Operations ─────      │  │                                              │  │
│  │ [Import data]             │  │                                              │  │
│  │ [Export data]             │  │                                              │  │
│  │ [Screenshot]              │  │                                              │  │
│  │                           │  │                                              │  │
│  │ ──────────────────────    │  │                                              │  │
│  │ [Stop]                    │  │                                              │  │
│  └───────────────────────────┘  └──────────────────────────────────────────────┘  │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

If Kibana blocks iframe embedding (common for production-style deployments with X-Frame-Options DENY), the right pane uses `<sg-remote-browser>` instead — Neko/VNC tab-into-Kibana via remote desktop. Implementation: try iframe first; on `error` event from the iframe, fallback to `<sg-remote-browser>` automatically. **The user doesn't see the difference.**

The "Operations" panel (Import / Export / Screenshot) buttons are stubs in this brief — they fire `sp-cli:elastic.import-requested` etc.; backend handlers come later.

### Playwright detail

Playwright's centre of gravity is browser automation — controls + screenshot/result viewer:

```
┌─[ Playwright: playwright-fast-bohr × ]──────────────────────────────────────────────┐
│                                                                                      │
│  ┌─[ Controls ]──────────────┐  ┌─[ Result Viewer ]────────────────────────────────┐ │
│  │                           │  │                                                   │ │
│  │ ●Ready · 3m               │  │ Latest screenshot                                 │ │
│  │ Containers:               │  │ ┌────────────────────────────────────────────┐    │ │
│  │   playwright-1 ●          │  │ │                                            │    │ │
│  │   mitm-proxy   ●          │  │ │   [Screenshot rendered here]               │    │ │
│  │                           │  │ │                                            │    │ │
│  │ ─── Actions ─────         │  │ │                                            │    │ │
│  │ [Take screenshot]         │  │ │                                            │    │ │
│  │ [Run sequence]            │  │ └────────────────────────────────────────────┘    │ │
│  │ [Open MITM proxy UI]      │  │                                                   │ │
│  │ [View traffic log]        │  │ Last action: take_screenshot at 02:43:18         │ │
│  │ [View logs]               │  │                                                   │ │
│  │                           │  │                                                   │ │
│  │ ──────────────────────    │  │                                                   │ │
│  │ [Stop]                    │  │                                                   │ │
│  └───────────────────────────┘  └───────────────────────────────────────────────────┘ │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

The "Open MITM proxy UI" button → opens `<sg-remote-browser>` in a third tab pointing at the mitmweb URL (since mitmweb often blocks iframes too).

**Note:** This is the *Playwright* compute type — for SP-CLI's *use* of Playwright internally (the existing browser automation service that this whole repo started as). The plugin folder is `playwright/` and reflects the historical SG-Playwright service.

### VNC detail — full panel, no split

VNC needs **maximum screen real estate** for the remote desktop. The detail tab is just `<sg-remote-browser>` filling the entire pane:

```
┌─[ VNC: vnc-sharp-maxwell × ]──────────────────────────────────────────────────────┐
│                                                                                    │
│  vnc-sharp-maxwell                          ⇄ Mitmweb       ↗ New tab     [Stop]   │
│  ─────────────────────────────────────────────────────────────────────────────     │
│                                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                              │  │
│  │                    [Remote desktop browser-in-browser fills here]            │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  │                                                                              │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Controls — Stop, status, view-mitmweb toggle — go in a slim toolbar above the remote browser. Status (●Ready, uptime) on the left; controls on the right.

This is **almost exactly what shipped in the existing `<sp-cli-vnc-viewer>` component** — that component is **promoted to `<sg-remote-browser>`** in `_shared/` and the VNC detail just composes it with a slim header.

### Prometheus / OpenSearch detail

Similar shape to Elastic — info pane + service-UI pane. Stub implementations using the shared widgets, no special operations. Get added when the underlying compute types go available.

## Storage view (placeholder)

The Left Nav has Storage. Click → main column shows the Storage view. **For this brief, Storage is a placeholder** — a single panel saying:

```
Storage

(Vault browser and S3 status coming in a follow-up brief.)

Currently connected:
  🗝 vault: clear-twig-0823 (read+write)
  Endpoint: https://send.sgraph.ai
  4 files · 12 KB

[Browse vault contents in vault-peek →]
```

The "Browse" link opens `https://dev.vault.sgraph.ai/en-gb/#{vault-id}` in a new browser tab. That's the existing vault browser; deep-linking is the easy delivery.

## Settings view

```
┌─[ Settings ]─────────────────────────────────────────────────────────────────┐
│                                                                               │
│  Compute Plugins                                                              │
│  ──────────────                                                               │
│                                                                               │
│  [✓] 🐧 Bare Linux                stable          ~60s boot                   │
│  [✓] 🐳 Docker host               stable          ~10min boot                 │
│  [✓] 🔍 Elastic + Kibana          stable          ~90s boot                   │
│  [✓] 🖥 VNC bastion                stable          ~90s boot                   │
│  [ ] 📊 OpenSearch + Dashboards   experimental    coming soon                 │
│  [ ] 🌐 Neko (WebRTC browser)     experimental    coming soon                 │
│  [ ] 🎯 Prometheus                 experimental    coming soon                 │
│                                                                               │
│  Toggling a plugin shows or hides its launcher card immediately.              │
│                                                                               │
│  ─────────────────────────────                                                │
│                                                                               │
│  UI panels                                                                    │
│  ──────────                                                                   │
│                                                                               │
│  [✓] Events Log (right panel)                                                 │
│  [✓] Vault Status (right panel)                                               │
│  [✓] Active Sessions (right panel)                                            │
│  [✓] Cost Tracker (right panel)                                               │
│                                                                               │
│  ─────────────────────────────                                                │
│                                                                               │
│  Defaults                                                                     │
│  ────────                                                                     │
│                                                                               │
│  Default region:        [eu-west-2 ▾]                                         │
│  Default auto-stop:     [4 hours ▾]                                           │
│  Default instance size: [t3.medium ▾]                                         │
│                                                                               │
│  ─────────────────────────────                                                │
│                                                                               │
│  Layout                                                                       │
│  ──────                                                                       │
│                                                                               │
│  [Reset layout to default]   ← clears saved sg-layout state                   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

Toggle a plugin → fires `sp-cli:plugin.toggled { name, enabled }`. Compute view's launcher pane listens, re-renders. Settings persisted to `sp-cli/preferences.json` in vault.

Toggle a UI panel → fires `sp-cli:ui-panel.toggled { panel, visible }`. Page controller listens, hides/shows the right-panel section.

## Diagnostics view (placeholder)

Similar shape to Storage — panel saying "Real-time API status, error log, and system health coming in a follow-up brief." Show: API URL, current vault ID, browser info, last few errors from console (if any).

## Right info column

Four stacked panels, all reading live from events:

### Events Log

```
┌─[ Events Log ]────────────────────┐
│                                    │
│ 02:43:18  🌐 vault:read-completed  │
│           sp-cli/preferences.json  │
│           1.2 KB · 87ms            │
│                                    │
│ 02:43:14  📋 sp-cli:stack.launched │
│           elastic-loud-noether     │
│                                    │
│ 02:43:08  ⚙ core:plugin.loaded    │
│           vnc · stable             │
│                                    │
│ 02:43:08  🗝 vault:connected       │
│           clear-twig-0823          │
│                                    │
│ Filter: [all ▾] [Clear]            │
└────────────────────────────────────┘
```

Listens for **all** events on `document` (using a wildcard handler that captures events with the right naming pattern). Filter dropdown lets the operator narrow to: All / Vault / Stacks / Plugins / Errors.

This is the existing `<sp-cli-vault-activity>` component **generalised** — it currently only listens for `sp-cli:vault-bus:*`; the new version is broader. Rename to `<sp-cli-events-log>`. Keep the existing one as deprecated for one release if needed.

### Vault Status

```
┌─[ Vault Status ]──────────────────┐
│                                    │
│ ✅ Connected                       │
│ 🗝 clear-twig-0823                 │
│ send.sgraph.ai · read+write       │
│                                    │
│ 4 files · 12 KB                    │
│ Last sync: 2 min ago               │
│                                    │
│ [Browse →]                         │
└────────────────────────────────────┘
```

Reads from `vault-bus.js` `currentVault()`. Updates on `vault:connected` / `vault:disconnected`.

### Active Sessions

```
┌─[ Active Sessions ]───────────────┐
│                                    │
│ • dinis@sgraph.ai     3h 12m       │
│   (this browser)                   │
│                                    │
│ (Multi-user tracking coming        │
│  with per-instance API.)           │
└────────────────────────────────────┘
```

Placeholder for now. Just shows the current operator (from vault key as a stand-in for identity). Multi-user tracking lands when the per-instance FastAPI brief lands.

### Cost Tracker

```
┌─[ Cost Tracker ]──────────────────┐
│                                    │
│ Today (placeholder):               │
│   t3.medium  4h 12m   $0.41        │
│   t3.large   2h 20m   $0.41        │
│   ─────────────                    │
│   Total              $0.82         │
│                                    │
│ (Real cost calculation coming      │
│  with billing brief.)              │
└────────────────────────────────────┘
```

Placeholder. Computes mock cost from active stacks × instance type rate. Real cost calculation is its own brief.

## Visual language

Same `sg-tokens.css` as before. Colours, spacing, typography all from the canonical Tools tokens. No new CSS variables in this brief.

Specific changes:

- **Status badge for plugin stability**: `stable` (no badge), `experimental` (small amber badge), `deprecated` (small grey strikethrough).
- **Tab close button**: Tabs created from the launcher / detail-view pattern have a `×` close button. Locked tabs (Stacks pane, default panes) don't. Existing sg-layout pattern.
- **Slim toolbars**: Detail views often have a slim toolbar above the main content (e.g., VNC's [Stop] button row). 32px high, neutral bg.

## Empty / loading / error states — extend the existing patterns

| Trigger | Treatment |
|---|---|
| Vault not connected | Same as today — page dimmed with "Connect a vault" prompt |
| No active stacks | "No stacks running. Launch one from the Launcher above ↑" with arrow |
| No catalog types (all disabled) | "All compute plugins are disabled. Enable some in [Settings →]" |
| Catalog endpoint 500 | Toast + retry; cached catalog from vault if available |
| Detail tab opened for a stack that just got deleted | "This stack no longer exists." with [Close tab] |
| Plugin toggled off while detail tab is open | Tab auto-closes with toast: "Closed Linux detail (plugin disabled)" |

## What good looks like

When the rebuild is done, an operator should be able to:

- Open the page → vault connects → 3-column layout appears.
- Click any plugin's [Launch] → tab opens with the form → fill → submit → tab auto-closes → new stack appears in the table.
- Click any stack row → type-specific detail tab opens.
- Open multiple detail tabs → switch between them via the tab bar.
- Drag splitters to resize panels → reload → same sizes.
- Toggle Neko in Settings → tab badge says "✓ saved to vault" → the Neko card appears in the launcher immediately.
- Watch events fire in real time in the right column.
- **Never see a modal dialog.**

If any of those is wrong, the rebuild is not done.
