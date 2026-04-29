# 01 — Visual Design

**Status:** PROPOSED
**Read after:** `README.md`
**Read alongside:** `02__component-architecture.md` when implementing

---

## What this doc gives you

The full visual design for the next version of `/admin/` and `/user/`. Layouts, mockups, interaction states, the visual language to mirror, the things to avoid. Concrete enough that you can build the HTML/CSS without a design review round-trip.

## The reference: cloud-provider consoles

The Playwright provisioning UI is fundamentally a **resource console** — operators come to it to launch, observe, and tear down ephemeral compute. That's the same shape AWS Console solves, that GCP Console solves, that Azure Portal solves. We're not inventing visual language; we're inheriting it.

### What to mirror from AWS

- **Persistent top bar** with brand-left, identity-right.
- **Resource-list-as-default-page** — the operator wants to see what's running, immediately, without clicking.
- **Primary `[Launch]` CTA top-right of the resource list**, opens a wizard.
- **Status colour conventions** — green for running, amber for pending/transitional, red for failed/error, grey for stopped/inactive — accompanied by text labels (never colour alone, accessibility).
- **Detail-panel-on-row-click** that doesn't navigate away. The list stays visible (dimmed); the panel slides in from the right.
- **Monospace for resource identifiers** — instance IDs, AMI IDs, security group IDs.
- **Explicit confirmation before destructive actions** — Stop, Terminate, Delete.
- **Region picker prominent** — one of the most common operator actions is changing region. AWS puts it top-right. We do too.

### What to avoid from AWS

- AWS's *information density.* Tiny rows, tiny fonts, columns crammed against each other. Our table rows are ~48px tall; AWS's are ~28px. Operators on this UI for 5 minutes need to find things, not scan dense data.
- AWS's *visual noise.* Gradients, drop shadows, secondary borders, subtle backgrounds within subtle backgrounds. We use one elevation level for cards; flat surfaces otherwise.
- AWS's *colour overuse.* AWS uses orange, blue, purple, and red as feature accents in the same view. We use one accent (the SGraph teal `#4ECDC4` from `sg-tokens.css`) and the four status colours. Period.

### What to mirror from GCP

- The *spacing.* GCP gives content room to breathe. 16–24px row padding, generous whitespace between sections.
- The *colour restraint.* One accent, semantic colours for status, otherwise neutral.

### What's different in this product

- **Vault as identity.** AWS shows the AWS account, top-right. We show the connected vault. Same affordance, our concept.
- **No region per resource (yet).** AWS displays each resource's region in the table; for the MVP we're effectively single-region (`eu-west-2`). The region picker is global to the page.

---

## The two pages

### Top bar — shared between admin and user

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ┃SGraph┃  Provisioning Console            eu-west-2 ▾   🗝 clear-twig-0823 ▾  │
└────────────────────────────────────────────────────────────────────────────────┘
        ↑                ↑                          ↑                  ↑
        │                │                          │                  │
        Brand mark       Console title               Region picker     Vault picker
        (links to home)  (page lens: "Admin"         (scopes resource  (the equivalent
                          or "Provisioning")          listings)         of AWS account
                                                                        in our model)
```

- **Brand mark** is the SGraph wordmark; clicking it goes to the index page.
- **Console title** changes per page: "Provisioning Console" on user, "Admin Dashboard" on admin. This is the *only* visual cue to which page you're on, and that's intentional — the audiences are different but the visual chrome is identical.
- **Region picker** is a dropdown defaulting to `eu-west-2`. For MVP, the only region available is `eu-west-2`; the dropdown shows it as the only option, but the chrome is in place for when others land.
- **Vault picker** rightmost. See "Vault picker UX" below.

Height: 56px. Background: `var(--sg-bg-secondary)`. Bottom border: 1px `var(--sg-border)`.

### Vault picker UX

Click the vault picker → dropdown:

```
┌──────────────────────────────────────────────┐
│ Connected vault                              │
│   🗝 clear-twig-0823                         │
│      send.sgraph.ai · readKey                │
│      4 files · 2 folders · 12 KB             │
│                                              │
│ ──────────────────────────────────────────── │
│ Recent vaults                                │
│   🗝 storm-crisp-0285  (3 days ago)          │
│   🗝 quiet-fermi-1234  (1 week ago)          │
│                                              │
│ ──────────────────────────────────────────── │
│ [+ Connect another vault]                    │
│ [+ Create new vault]                         │
│ [⚙ Vault settings]                           │
│                                              │
│ [Disconnect vault]                           │
└──────────────────────────────────────────────┘
```

- Top: the current vault's identity, endpoint, and stats (file/folder count, size — read from `session.treeModel.getStats()` on connect).
- Middle: recent vaults from localStorage history. Clicking switches to that vault (re-prompting for both vault key and access token — neither is persisted across vault switches).
- Bottom: actions. "Connect another vault" opens the two-field connect form below. "Create new vault" is the brand-new-vault flow using `core/vault-init/`. "Vault settings" navigates to the Settings tab where the operator can see/copy the vault ID, endpoint, and stored access-token name (never the actual values).

### Two-secret connect form

When the operator chooses to connect (either first time or after switching), the form prompts for **both secrets explicitly**:

```
┌─────────────────────────────────────────────────────────────────┐
│  Connect to a vault                                       [✕]   │
│  ─────────────────────                                          │
│                                                                 │
│  Vault key  (the "DB connection string")                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ word-word-1234   or   passphrase:vaultId               │    │
│  └─────────────────────────────────────────────────────────┘    │
│  Read-only access works with this alone.                        │
│                                                                 │
│  Access token  (needed for writes — leave blank for read-only)  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ••••••••••••••••••••                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│  Issued by the vault server. Without this, preferences and      │
│  activity log won't persist.                                    │
│                                                                 │
│  Endpoint                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ https://send.sgraph.ai                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ☑ Remember on this device  (stored in localStorage)            │
│                                                                 │
│                                       [ Cancel ]  [ Connect → ] │
└─────────────────────────────────────────────────────────────────┘
```

Field semantics:

- **Vault key** — the data-access secret. Equivalent to a database connection string. Format is `word-word-NNNN` (simple token) or `passphrase:vaultId` (full key). Drives key derivation and gives the bearer access to read/decrypt the vault's contents.
- **Access token** — the server-write secret. Equivalent to push permission. Without it, all write operations fail and the UI works in read-only mode (which means preferences and activity log don't persist across page reloads — the operator gets a banner: "Read-only — writes disabled. Reconnect with an access token to save preferences and activity history.")
- **Endpoint** — defaults to `https://send.sgraph.ai`. Operators rarely change this.
- **Remember on this device** — when checked (default), both secrets are stored in `localStorage` under `sp-cli:vault:last-read-key` and `sp-cli:vault:last-access-token`. **The brief calls this out explicitly** because storing access tokens in localStorage is a real trade-off — convenient for operators, less secure than browser-credential APIs. For MVP, the convenience wins. A follow-up brief can move to `<sg-credential-store>` (Tools' password-manager wrapper) if the threat model warrants.

The form is rendered using `<sg-vault-connect>` from Tools — its existing UI already has both fields. The "two-secret" framing in this brief is mostly about how the *picker* and the *help text* present the fields to operators, so they understand what each does.

The "no vault connected" state replaces the picker dropdown content with a primary CTA: `[Connect a vault →]` — and it dims the rest of the page until a vault is connected. **No vault, no UI.**

### Read-only banner

When a vault is connected with a vault key but no access token (`isWritable() === false`), the top bar shows a small amber banner just below it:

```
⚠ Read-only — writes disabled. [Add access token →]
```

Clicking the link reopens the connect form pre-filled with the existing vault key, prompting only for the access token. Operators don't have to re-paste the vault key.

---

## The user page — `/user/`

The user page leads with **the action you came to take**: launching a stack.

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ┃SGraph┃  Provisioning Console            eu-west-2 ▾   🗝 clear-twig-0823 ▾  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  Start a new environment                                                       │
│                                                                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌─────────────┐   │
│  │ 🐧 Linux        │  │ 🐳 Docker       │  │ 🔍 Elastic      │  │ 🖥 VNC      │   │
│  │                 │  │                 │  │                 │  │ COMING SOON │   │
│  │ Bare AL2023.    │  │ AL2023 with     │  │ Elastic +       │  │             │   │
│  │ SSM access.     │  │ Docker CE.      │  │ Kibana on EC2.  │  │             │   │
│  │                 │  │                 │  │                 │  │             │   │
│  │ ~60s boot       │  │ ~10min boot     │  │ ~90s boot       │  │  disabled   │   │
│  │                 │  │                 │  │                 │  │             │   │
│  │ [   Launch   ]  │  │ [   Launch   ]  │  │ [   Launch   ]  │  │             │   │
│  └────────────────┘  └────────────────┘  └────────────────┘  └─────────────┘   │
│                                                                                │
│  ─────────────────────────────────────────────────────────────────────────     │
│                                                                                │
│  Active stacks                                                                 │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ 🐧 linux-quiet-fermi   ●Ready  18.132.60.220   4m   [Details] [Stop]    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ 🐳 docker-bold-curie   ◐Boot   —              32s   [Details] [Stop]    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

Sections, top to bottom:

1. **Top bar** (shared, 56px).
2. **"Start a new environment" — the type cards.** Four cards, side by side. Live ones (Linux, Docker, Elastic) have a `[Launch]` button. "Coming soon" tiles (VNC, OpenSearch if not yet mounted) are visibly different — desaturated, no button. Each card shows the type name with emoji, a one-line description, expected boot time, and the action.
3. **Active stacks strip.** Stacked cards (one per running stack) with type icon, name, status (dot + label), public IP (or "—" if not yet ready), uptime, action buttons. Clicking `[Details]` opens the detail panel. Clicking `[Stop]` opens a confirmation modal.

When there are no active stacks: the section header is followed by a small empty state: *"Nothing running right now. Launch one above ↑"*.

### sg-layout on the user page — simpler than admin

The user page also uses `<sg-layout>` for consistency, but the default layout is single-pane (just the main content). The vault activity pane is **collapsed by default** but available as a slide-out from the right edge:

```javascript
{
    type: 'row',
    sizes: [1.0, 0.0],   // vault pane starts collapsed (0 width)
    children: [
        {
            type: 'stack',
            tabs: [
                { tag: 'sp-cli-user-pane', title: 'Provision', locked: true },
            ],
        },
        {
            type: 'stack',
            tabs: [
                { tag: 'sp-cli-vault-activity', title: 'Vault Activity', locked: true },
            ],
        },
    ],
}
```

A small `[Vault activity ▶]` button in the top-right of the user page expands the activity pane (giving it ~25% width). For the cleanest user-facing demo, leave it collapsed by default — operators who want to see vault traffic can open it.

### The user page launch wizard

Click `[Launch]` on a type card → modal opens:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Launch a Linux stack                                                     [✕]  │
│  ────────────────────                                                          │
│                                                                                │
│  Stack name              [auto-generated if blank          ]                   │
│  Region                  [eu-west-2                       ▾]                   │
│  Instance type           [t3.medium                       ▾]                   │
│  Auto-stop after         [4 hours                         ▾]                   │
│                                                                                │
│  ▾ Advanced (collapsed)                                                        │
│                                                                                │
│  ─────────────────────────────────────────────────────────                     │
│                                                  [ Cancel ]    [ Launch → ]    │
└────────────────────────────────────────────────────────────────────────────────┘
```

The form:

- **Stack name** — optional. Backend generates one if blank.
- **Region** — defaults from vault preferences if available, else `eu-west-2`.
- **Instance type** — defaults from the catalog entry's `default_instance_type`. Dropdown of valid options.
- **Auto-stop after** — defaults from catalog `default_max_hours`. Dropdowns: 1h / 2h / 4h / 8h / 24h.
- **Advanced** disclosure — for MVP this is empty; placeholder for future fields (extra ports, custom AMI, etc.).

Click `[Launch →]` → modal transitions to **progress state**:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Launching linux-quiet-fermi                                              [✕]  │
│  ─────────────────────────                                                     │
│                                                                                │
│  ✅ Stack created             0:03                                             │
│  ✅ Instance pending          0:08                                             │
│  ◐  Instance running          0:32  ← spinner                                  │
│  ☐  Waiting for SSM…                                                           │
│  ☐  Ready                                                                      │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐           │
│  │ ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  0:32 / ~1:00
│  └─────────────────────────────────────────────────────────────────┘           │
│                                                                                │
│  This window stays open until ready.                                           │
│  You can close it anytime — the stack continues launching in the background.   │
│                                                                                │
│                                                       [ Run in background ]    │
└────────────────────────────────────────────────────────────────────────────────┘
```

The progress display has **explicit checkpoint steps**:

- ✅ — checkpoint reached
- ◐ — in progress (animated spinner)
- ☐ — not yet reached

Each checkpoint corresponds to a specific health-check transition. The checkpoints for Linux/Docker/Elastic:

| Step | Reached when |
|---|---|
| Stack created | `POST /{type}/stack` returns 200 |
| Instance pending | First health response with state in `{PENDING, INITIALIZING}` |
| Instance running | First health response with state `RUNNING` |
| Waiting for SSM | `state=RUNNING` AND `ssm_reachable=false` (only for types where SSM matters — linux/docker; elastic has its own health protocol) |
| Ready | `healthy=true` |

The progress bar interpolates between known checkpoints (each contributes 20-25% to the bar), and against the catalog `expected_boot_seconds` between checkpoint transitions. Caps at 95% until `healthy=true`.

`[Run in background]` and the `[✕]` both close the modal **without cancelling the launch**. The user returns to the page; the active stack appears in the active-strip in its current state (PENDING/RUNNING/etc.) and continues progressing until it's READY. **This is the most important UX fix in the brief** — currently, closing the modal abandons the SSM command forever.

When the stack reaches READY:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ✅ linux-quiet-fermi is ready                                            [✕]  │
│  ──────────────────────────────                                                │
│                                                                                │
│  Public IP: 18.132.60.220 · Region: eu-west-2 · Took 0:54                      │
│                                                                                │
│  Connect via SSM                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │ aws ssm start-session --target i-0a1b2c3d…                          │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│  [📋 Copy command]                                                              │
│                                                                                │
│  Auto-stops in 3h 59m. You can stop it earlier from the active list.           │
│                                                                                │
│                                            [ Open details ]    [ Done ]        │
└────────────────────────────────────────────────────────────────────────────────┘
```

`[Open details]` closes the modal and opens the detail panel. `[Done]` just closes. Either way, all the information stays available via the detail panel from the active strip.

---

## The admin page — `/admin/`

The admin page is a **multi-pane layout** built with `<sg-layout>` — a top bar across the top, then a body split into resizable columns. Operators can drag splitters, collapse panes, and switch tabs. Layout state is preserved in `localStorage` so the operator's preferred sizing carries across reloads.

The default layout looks like this:

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ ┃SGraph┃  Admin Dashboard                       eu-west-2 ▾   🗝 clear-twig-0823 ▾  │
├────────────────────────────────────────────────────────────────────────────────────┤
│ ⚠ Read-only — writes disabled. [Add access token →]            ← only when no token │
├──────────────────────────────────────────────────────────┬─────────────────────────┤
│ ┌─[ Stacks │ Catalog │ Activity Log ]──────────────────┐ │ ┌─[ Vault Activity ]──┐ │
│ │                                                       │ │                        │
│ │ Active stacks                       [+ Launch ▾]      │ │ 🔑 vault-key:ready    │
│ │                                                       │ │    clear-twig-0823    │
│ │ Filter: [all ▾] [running ▾]   🔍 search               │ │    (0 ms)             │
│ │                                                       │ │                        │
│ │ ┌─────┬─────────────────┬────────┬──────────┬───┐    │ │ 🌐 fetch-started      │
│ │ │     │ Name            │ State  │ IP       │   │    │ │    sp-cli/active-st…  │
│ │ ├─────┼─────────────────┼────────┼──────────┼───┤    │ │    obj-cas-imm-a3f4   │
│ │ │ 🐧  │ linux-quiet-…  │ ●Ready │ 18.132…  │ ⋯ │    │ │ ✅ fetch-completed    │
│ │ │ 🐳  │ docker-bold-…  │ ◐Boot  │ —        │ ⋯ │    │ │    1.2 KB · 87 ms     │
│ │ │ 🔍  │ elastic-loud-… │ ●Ready │ 3.10.42… │ ⋯ │    │ │ 🔓 decrypt-completed  │
│ │ └─────┴─────────────────┴────────┴──────────┴───┘    │ │    1.1 KB · 12 ms     │
│ │                                                       │ │ 📄 content-ready      │
│ │ ──────────────────────────────────────────            │ │    JSON · 3 stacks    │
│ │                                                       │ │                        │
│ │ Stack types                                           │ │ ✏  write-started      │
│ │ ┌──────┬──────┬──────┬──────┐                         │ │    sp-cli/activity-…  │
│ │ │Linux │Docker│Elast.│ VNC  │                         │ │    256 B              │
│ │ │  ✓   │  ✓   │  ✓   │ soon │                         │ │ ✅ write-completed    │
│ │ │[Lnch]│[Lnch]│[Lnch]│ —    │                         │ │    commit abc123…     │
│ │ └──────┴──────┴──────┴──────┘                         │ │    142 ms             │
│ │                                                       │ │                        │
│ └───────────────────────────────────────────────────────┘ │  [Clear] [Filter ▾]   │
│                                                           │                        │
│  drag this splitter ↕ to resize                           │ │                      │
│                                                           │                        │
└───────────────────────────────────────────────────────────┴────────────────────────┘
```

The layout is built from this sg-layout JSON:

```javascript
{
    type: 'row',
    sizes: [0.72, 0.28],                                            // 72/28 split, resizable
    children: [
        // Left column: tabbed main content
        {
            type: 'stack',
            tabs: [
                { tag: 'sp-cli-stacks-pane',     title: 'Stacks',       locked: true },
                { tag: 'sp-cli-catalog-pane',    title: 'Catalog',      locked: false },
                { tag: 'sp-cli-activity-pane',   title: 'Activity Log', locked: false },
            ],
        },
        // Right column: vault activity tracer
        {
            type: 'stack',
            tabs: [
                { tag: 'sp-cli-vault-activity', title: 'Vault Activity', locked: true },
            ],
        },
    ],
}
```

Sections, top to bottom:

1. **Top bar** (shared, 56px).
2. **Read-only banner** — only present when access token is missing; goes away once a token is added.
3. **Main content stack (left)** — tabbed:
   - **Stacks** — the resource list + type strip + filters (default tab; locked so it can't be closed).
   - **Catalog** — admin-only catalog overrides editor (placeholder for MVP; the tab exists but the editor is post-MVP).
   - **Activity Log** — the application-level activity log (launches, stops, ready transitions) read from `sp-cli/activity-log.json`.
4. **Vault Activity (right)** — live trace of every read and write the page makes against the vault. See "Vault activity pane" below.
5. **Splitters** — operators can drag the vertical splitter between the columns, and any horizontal splitters within nested layouts. State is saved.

`[+ Launch stack ▾]` top-right of the Stacks tab opens a small picker — choose Linux / Docker / Elastic / (disabled VNC) — then opens the same launch wizard the user page uses.

### Vault activity pane

The right pane is a **live trace** of every vault interaction the page makes. It's the operator's window into "is the vault working?". Each line shows: an icon for the operation type, the operation name, the path or short file ID, the size and latency.

```
🔑 vault-key:ready             clear-twig-0823 · 0ms
📋 manifest:loaded             4 files · 87ms
🌐 fetch-started               sp-cli/active-stacks-cache.json
                               obj-cas-imm-a3f4d2…
✅ fetch-completed             1.2 KB · 87ms
🔓 decrypt-completed           1.1 KB · 12ms
📄 content-ready               JSON parsed · 3 stacks

✏  write-started               sp-cli/activity-log.json · 256B
✅ write-completed             commit abc123de · 142ms

🔴 fetch-error                 sp-cli/preferences.json
                               404 Not Found
                               (treated as "use defaults")
```

The pane has:

- **Auto-scroll** — newest entries at the top, automatically scrolling as new entries arrive.
- **Pause** — click the pane to freeze auto-scroll while reading. Click [Resume] (appears) to re-engage.
- **Filter** — `[Filter ▾]` dropdown lets the operator hide categories (just-reads, just-writes, errors-only).
- **Clear** — `[Clear]` button empties the displayed trace (does not affect vault data).
- **Persistent across re-renders** — entries stay until cleared or page reload.

Implementation: a new component `<sp-cli-vault-activity>` that listens for vault-bus events (see doc 03's "vault-bus events" section). The component re-uses the visual pattern from `<sg-vault-trace>` in Tools but covers the vault-bus event vocabulary (which includes write events that `<sg-vault-trace>` doesn't track today).

Why a new component instead of `<sg-vault-trace>`: doc 03 explains in detail. Short version — `<sg-vault-trace>` only listens for `sg-vault-fetch:*` and `sg-vault-key:*` events fired by the embed components, but vault-bus uses the function-API directly and emits its own `sp-cli:vault-bus:*` events. The new component covers both.

### Default layout state and operator overrides

The layout JSON above is the default. On first load, sg-layout uses it. As the operator drags splitters, sg-layout serialises the current state and stores it under `sp-cli:admin:layout` (well, `sg-layout` does this internally — check the latest sg-layout API for the exact state-persistence hook). Subsequent page loads restore the operator's preferred sizing and tab order.

A `[Reset layout]` button in Settings (and a developer-mode keyboard shortcut Ctrl+Shift+L) restores the default layout.

### The detail panel — used on both pages

Click any row in the active list (or any active-strip card on user page) → detail panel slides in from the right. Both pages use the same panel.

```
┌────────────────────────────────────────────┬───────────────────────────────────┐
│ ... (table dimmed, possibly width reduced) │ linux-quiet-fermi             [✕] │
│                                            ├───────────────────────────────────│
│                                            │ ●Ready · running 4m 32s           │
│                                            │ Type: t3.medium · eu-west-2       │
│                                            │ Launched: 2026-04-29 01:38:14     │
│                                            │ Auto-stops in: 3h 55m             │
│                                            │                                   │
│                                            │ ──── Connect via SSM ────         │
│                                            │ ┌──────────────────────────────┐  │
│                                            │ │ aws ssm start-session       │  │
│                                            │ │   --target i-0a1b2c3d…       │  │
│                                            │ └──────────────────────────────┘  │
│                                            │ [📋 Copy]                          │
│                                            │                                   │
│                                            │ ──── Network ────                 │
│                                            │ Public IP:  18.132.60.220         │
│                                            │ Allowed IP: 82.46.x.x              │
│                                            │ SG:         sg-0a1b2c3d           │
│                                            │                                   │
│                                            │ ▾ Resource details (collapsed)    │
│                                            │   AMI:           ami-…             │
│                                            │   Instance ID:   i-0a1b2c3d…      │
│                                            │   Name tag:      linux-quiet-…    │
│                                            │   Allowed ports: 22 (SSM)         │
│                                            │                                   │
│                                            │ ▾ Recent activity                 │
│                                            │   01:42  health: ssm-reachable    │
│                                            │   01:40  health: running           │
│                                            │   01:38  health: pending           │
│                                            │   01:38  launched                  │
│                                            │                                   │
│                                            │ ─────────────────────────────     │
│                                            │ [Stop stack] [Restart] [Resize]   │
│                                            │ ⚠ Stop confirms before acting     │
└────────────────────────────────────────────┴───────────────────────────────────┘
```

Sections of the panel, top to bottom:

1. **Header line** — name, close button.
2. **Status summary** — state with dot, uptime, type, region, launched time, auto-stop countdown.
3. **Connect via SSM** — the most important section. Full SSM command with copy button. Always-visible while the stack is `RUNNING` or `READY`.
4. **Network** — public IP, allowed IP (the `caller_ip` that's whitelisted in the security group), security group ID.
5. **Resource details** — collapsed by default. AMI, instance ID, name tag, allowed ports.
6. **Recent activity** — last few state transitions. Read from this stack's section of the activity log.
7. **Actions** — Stop (always shown), Restart and Resize (greyed for now; placeholder for future).

When the stack is in a non-terminal state (PENDING, INITIALIZING, RUNNING but not ready), the SSM section shows a placeholder: *"SSM command available once the stack is ready (~30s remaining)"*.

`[Restart]` and `[Resize]` are visually present but disabled in the MVP. Hover tooltip: *"Coming soon"*. They're there to set expectation that this is the place future actions live.

---

## States — empty, loading, error

### Empty states

| Page | State | Treatment |
|---|---|---|
| User page, no active stacks | "Nothing running. Launch one above ↑" with arrow pointing to type cards. |
| Admin page, no active stacks | Empty table with one row: "No stacks running." Below the table, a small `[+ Launch a stack to populate this view]` button. |
| Admin page, no activity yet | "No activity yet. Launch a stack to see entries here." |
| Vault-not-connected (any page) | Page content dimmed and replaced with a single-card centred prompt: "Connect a vault to use this console" with `[Connect →]` opening the vault-key form. |

### Loading states

The first fetch on page load while the catalog and active stacks are being read from vault and FastAPI:

| Element | Loading shape |
|---|---|
| Type cards | Skeleton cards (same shape, animated grey shimmer) |
| Active stacks list | Skeleton rows (3 placeholder rows) |
| Activity log | Skeleton lines (5 placeholder lines) |

Skeletons fade out as data arrives. Avoid spinners — they're fine for transient operations (button presses, polling) but not for first paint.

### Error states

| Trigger | Treatment |
|---|---|
| FastAPI 401 | Top bar's vault picker turns amber with text "API key required" — clicking opens the API key input (the existing `<sg-auth-panel>` flow, kept for backwards compat with X-API-Key auth). |
| FastAPI 500 on a list endpoint | Toast: "Could not refresh stacks — using cached data". Active list shows last-known data with a subtle "stale" indicator. |
| Vault unreachable | Top bar vault picker turns red with text "Vault offline". Active list shows last-known cached data; writes are queued in memory until reconnect. |
| Health-check 500 during a launch | Wizard's progress display shows the current step in red with the error message, and offers `[Retry]` and `[Cancel and stop]`. |
| Component failed to load (e.g., Tools-import 404) | The component shows the `SgComponent.showError()` red box. Page continues working for everything else. |

---

## Visual language — concrete tokens

These reference `https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css`. Use the canonical names; do not introduce new variables in this brief.

| Concept | Token |
|---|---|
| Page background | `var(--sg-bg)` |
| Surface (cards, panels) | `var(--sg-bg-secondary)` |
| Surface (subtle, e.g. table headers) | `var(--sg-bg-surface)` |
| Border | `var(--sg-border)` |
| Body text | `var(--sg-text)` |
| Heading text | `var(--sg-text-heading)` |
| Muted / secondary text | `var(--sg-text-muted)` |
| Primary accent (buttons, links) | `var(--sg-accent)` |
| Accent hover | `var(--sg-accent-hover)` |
| Subtle accent (hover bg, badges) | `var(--sg-accent-subtle)` |
| Danger | `var(--sg-danger)` |

Status dots (extend the palette via component-local CSS, since they're status-specific):

| Status | Colour | Notes |
|---|---|---|
| Ready, Running | `#4ECDC4` (teal/accent) — same as primary | "All good" reads green-adjacent |
| Pending, Initialising, Stopping | `#F4B942` (amber) | New token candidate `--sg-status-pending` |
| Failed, Error | `var(--sg-danger)` | Coral red |
| Stopped, Terminated | `var(--sg-text-muted)` | Greyed |
| Unknown | `var(--sg-text-muted)` | Same as stopped — hide in active lists |

The status-pending colour can be added to `sg-tokens.css` in a follow-up to Tools; for now, define locally in the relevant component. Document the addition as a follow-up TODO.

Spacing (use the `--sg-sp-N` scale; do not introduce new spacing values):

- Card padding: `var(--sg-sp-4)` (16px)
- Section gap: `var(--sg-sp-6)` (24px)
- Table row padding: `var(--sg-sp-3)` vertical / `var(--sg-sp-4)` horizontal (~12px / 16px)
- Top bar padding: `var(--sg-sp-2)` vertical / `var(--sg-sp-4)` horizontal

Typography:

- Display (page titles, top bar): `var(--sg-font-display)` — DM Sans
- Body: `var(--sg-font-body)` — DM Sans
- Resource IDs / SSM commands / IPs: `var(--sg-font-mono)` — JetBrains Mono

Radii:

- All cards, buttons, inputs: `var(--sg-radius)` (6px)
- Pills (status, badges): `var(--sg-radius-pill)` (9999px)

Transitions:

- Hover, focus, button-press: `var(--sg-transition-fast)` (150ms ease)
- Modal/panel slide-in: 200ms ease-out

---

## Interactions

| Action | Result |
|---|---|
| Click stack row | Detail panel slides in from right. Table dims. |
| Click panel close `[✕]` | Panel slides out. Table un-dims. |
| Click `[Stop]` button | Confirmation modal: "Stop linux-quiet-fermi? This will terminate the EC2 instance. [Cancel] [Stop stack]". |
| Click outside detail panel (on dimmed table) | Panel closes. |
| Press Escape with modal/panel/dropdown open | Closes the topmost open thing. |
| Click `[+ Launch stack ▾]` (admin) | Type picker dropdown. Choose type → wizard opens. |
| Click `[Launch]` on a type card (user) | Wizard opens directly. |
| Click `[📋 Copy]` next to SSM command | Command copied to clipboard. Button briefly shows "Copied ✓". |
| Click row in active log | (Polish): jumps to the corresponding stack's detail panel. Defer if time-pressured. |
| Open the page with a vault not connected | Page content dims; centred "Connect a vault" card overrides. |

---

## What good looks like

When a developer or designer looks at the finished pages, they should be able to say:

- "This looks like a console, not an admin panel."
- "I can see at a glance what's running."
- "I know where to launch a new stack."
- "Closing the wizard didn't lose my SSM command."
- "Clicking a row showed me everything without taking me to a different URL."
- "It looks like part of the SGraph product family" (because of `sg-tokens.css`).
- "This would scale if we add 50 more stack types — the catalog drives the cards."

If any of those is not true, the design is not done.
