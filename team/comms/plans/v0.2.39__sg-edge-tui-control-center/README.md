---
title: "SG/Edge TUI — Control Center brief (the action-capable cockpit over the local edge)"
version: v0.2.39
date: 2026-05-21
status: BRIEF — for the dev agent building the SG/Edge edge TUIs. No code yet.
role: Architect → Dev
audience: the dev agent extending sg_compute_specs/sg_edge/tui/
builds-on:
  - library/guides/v0.2.39__tui_cli_separation.md           # the one rule: TUI is a GUI over the CLI
  - library/dev_packs/v0.2.36__tui-startup-pack/01__tui-playbook.md
  - library/dev_packs/v0.2.36__tui-startup-pack/03__screen-idiom-catalogue.md
  - team/comms/plans/v0.2.38__sg-edge-tui/README.md          # the five exploratory screens
  - sgraph_ai_service_playwright__cli/tui/components/Tui__App.py   # converge onto this
  - sg_compute_specs/sg_edge/tui/source/SG_Edge__TUI__Data_Source.py  # the action seam already exists
  - sg_compute_specs/sg_edge/local/Local__Edge__Stack.py
related:
  - sg_compute_specs/sg_edge/README.md
  - library/guides/v0.2.36__sg-edge-local-user-guide.md
---

# SG/Edge TUI — Control Center

> **What this is.** A single, action-capable cockpit for the SG/Edge **local** edge:
> a full visual read of the deployed architecture *and* the ability to drive it —
> register / unregister slugs, fire a request, set up / tear down the edge — without
> leaving the screen. It is the "sixth conversation" promotion candidate: the screen
> that turns the five read-only explorations into one place an operator lives in.
>
> **Why it's a small build, not a rewrite.** The action surface already exists. The
> data-source seam (`SG_Edge__TUI__Data_Source`) defines `can_act()` +
> `register` / `unregister` / `request` / `setup` / `teardown`, and `Local_Source`
> already wires every one to the tested `Local__Edge__Stack`. **No screen calls them
> yet.** This brief is mostly: add an action panel + preview + confirm + journal over
> machinery that is already built and tested at the service layer.

---

## 1. The one rule this screen must obey (v0.2.39 separation guide)

A TUI is a GUI over the CLI. Every action the Control Center triggers **already has a
native home** — `sg edge local register|unregister|request|setup|teardown`. The screen
must call the **same backend** those commands call (it does, via the data source →
`Local__Edge__Stack`), never re-implement the work. Concretely, for this screen:

- **No TUI-exclusive capability.** Each action key maps 1:1 to an existing
  `sg edge local *` command. If you find yourself adding logic in the screen, push it
  down to `Local__Edge__Stack` and expose it as a CLI verb first.
- **Capability-gated actions (rule 5).** Read `source.can_act()`. Local → `True`
  (keys live). AWS → `False` (keys rendered greyed with a "pending Slice 5" reason; the
  keypress must **not** raise). Re-check after every poll — never cache "can act".
- **Preview before mutate (rule 6).** Destructive / creating actions show what they
  will do *first* (see §4), and the preview is itself reachable from the CLI
  (`sg edge local request` already simulates; add `--dry-run` to `register` if the
  preview needs a native home it doesn't yet have).
- **Debug Panel is the proof.** Every backend call the screen makes is logged to the
  shared `Debug__Event_Log` so the panel shows the CLI/stack call underneath each
  keypress — the GUI teaches the CLI under it.

---

## 2. Converge onto the shared component library (do not extend the old base)

Build the Control Center on **`sgraph_ai_service_playwright__cli/tui/components/Tui__App`**,
not the SG/Edge-local `SG_Edge__TUI__App__Base`. This is the convergence the separation
guide §7 calls for, and the Control Center is the first SG/Edge screen to do it.

`Tui__App` gives you for free: Header, a scrollable `#body`, the collapsible **Debug
Panel** on the right (`d` toggles, open by default), Footer, `r` refresh, `q` quit,
`set_body(markup)`, `log_event(category, message, detail, ok)`, and `set_interval`
polling via `refresh_seconds`. Implement `populate()` to render the body.

Carry across the two SG/Edge base extras that `Tui__App` lacks and are worth keeping:
**`?` help overlay** (context-aware) and **`e` OSC-52 card export**. Add them as
BINDINGS on the Control Center subclass (or, better, lift them into `Tui__App` in a
small shared-lib PR if the cf-logs screens want them too — coordinate, don't fork).
Drop the `t` theme toggle only if `Tui__App` already standardises themes; otherwise keep it.

> **Inject a shared `Debug__Event_Log`** into both the screen and the data source, so
> `source.register(...)` etc. record into the same feed the panel renders. Add
> `record`-on-action to the source (or wrap the calls in the screen) — keep it honest:
> log the *actual* `Local__Edge__Stack` method invoked.

---

## 3. Layout — one screen, two columns + a journal

Idioms combined (catalogue): **Reality Dashboard (#5)** for the left read + **Simulator
(#7)** for the preview + a thin action surface. ASCII intent (real widgets, not literal):

```
┌ SG/Edge Control Center · local · edge.sg-labs.local ─────────────┬ Debug ─────────┐
│ STATE                                   │ ACTIONS                │ 10:07:48 stack │
│  ✓ deployed   ✓ wildcard   fleet: 1     │  slug: [ alice____ ]   │  register alice│
│  zero_streak: 0/3                       │                        │  → A+TXT ok    │
│ ┌ Slugs (DataTable) ───────────────┐    │  [n] register          │ 10:07:50 dns   │
│ │ slug   state    backend          │    │  [N] register dormant  │  read _sg.*    │
│ │ alice  ● live   127.0.0.1:8080   │◀── │  [u] unregister (sel)  │                │
│ │ bob    ◐ dorm   —                │    │  [g] request   (sel)   │                │
│ └──────────────────────────────────┘    │  [S] setup  [X] teardn │                │
│ Checks                                  │                        │                │
│  · slug:bob dormant — Vault Waker…      │ PREVIEW (of next action)│               │
│                                         │  request alice → 200    │                │
│                                         │  welcome · 127.0.0.1:8080│               │
└─────────────────────────────────────────┴────────────────────────┴────────────────┘
 [n]register [u]unregister [g]request [S]setup [X]teardown · [r]refresh [d]debug [?]help [e]export [q]quit
```

- **Left — STATE (the read).** Reuse the existing pure renders — the deployment summary
  (`deployment_markup`) for infra + the **`DataTable`** slug inventory (promote the
  `SG_Edge__TUI__Screen__Slugs` widget approach; it gives cursor/scroll/select for free)
  + the checks list. This is the "full visual understanding of the deployed architecture"
  the screen exists for. The selected DataTable row is the target for `unregister`/`request`.
- **Right — ACTIONS.** An `Input` for the slug name (defaults to the selected row), and
  key-bound actions. Each action is one `source.*` call. After it runs, re-poll and
  re-render so the left column reflects the new reality immediately.
- **Right — PREVIEW.** Before firing, show the predicted effect of the *next* action (§4).
- **Far right — DEBUG PANEL.** `Tui__App`'s panel, fed by the shared event log.

Keep `populate()` pure-render: it reads the latest snapshot + builds markup via the
existing `*_markup()` helpers. Actions mutate via the source, then call `populate()`.

---

## 4. The action surface — precise behaviour

| Key | Action | Backend (native home) | Gate | Preview shown first |
|---|---|---|---|---|
| `n` | register slug (with backend) | `source.register(slug)` → `sg edge local register` | `can_act()` | "will write `<slug>` A + `_sg.<slug>` TXT=ip:port" |
| `N` | register dormant (A only) | `source.register(slug, with_backend=False)` → `… register --no-backend` | `can_act()` | "will write `<slug>` A only (dormant)" |
| `u` | unregister selected | `source.unregister(slug)` → `sg edge local unregister` | `can_act()` + a row selected | "will remove `<slug>` A + TXT" + **confirm** |
| `g` | request selected | `source.request(slug)` → `sg edge local request` | a row selected (read-only — no gate needed) | the simulated outcome (welcome/dormant/404 + backend) |
| `S` | setup edge | `source.setup()` → `sg edge local setup` | `can_act()` | "will create zone + wildcard + 1 proxy" |
| `X` | teardown edge | `source.teardown()` → `sg edge local teardown` | `can_act()` | "will delete local DNS + stack state" + **confirm** |

Rules for the surface:
- **`request` is read-only** — it simulates the proxy hot path; no gate, no confirm; just
  show the outcome (welcome / dormant / not-recognised + backend). This is the safest,
  highest-frequency action and the one that best teaches "how it works".
- **Destructive actions (`u`, `X`) require a confirm** — push a small `ModalScreen`
  (Textual `push_screen`) with the preview text and y/n. Do **not** fire on a single key.
- **Disabled state is rendered, never raised** — when `can_act()` is `False` (AWS target),
  the action rows show greyed with "pending Slice 5"; pressing the key shows the same hint
  via `notify`, it does not call the source.
- **Every action logs to the Debug Panel** — `log_event('stack', 'register alice', 'A+TXT', ok=True)`
  around the call, and on failure `ok=False` with the error.
- **Result feedback** — `notify(...)` toast on success/failure; the left column re-polls.

> **`request` after `register`** is the golden demo loop the local user guide already
> documents: register alice → request alice → "Welcome to the alice vault". The Control
> Center should make that loop a three-keystroke experience (`n`, then `g` on the row).

---

## 5. Targets, head-less, and honesty

- **`--target local` (default)** — actions live (`can_act()=True`). This is the primary
  experience and the only one with mutations until Slice 5.
- **`--target aws`** — read the live `edge.sg-labs.app` registry (real topology/slugs),
  but `can_act()=False`: the STATE column is fully populated, the ACTION column is greyed
  with "pending Slice 5 (live EC2)". This is honest and is exactly what the guide's rule 5
  is for. (When Slice 5 lands and `AWS_Source.can_act()` flips to `True`, the keys light
  up with zero screen changes.)
- **Head-less / piped / `$TERM=dumb`** — print the read-only state card (reuse
  `SG_Edge__TUI__Card`) **plus a footer listing the native command for each action**
  (`register → sg edge local register <slug>`, …). Per separation-guide rule 3: a control
  TUI piped does **not** mutate — it shows state and points at the CLI.
- **Pending panes stay pending** — cost / throughput / instances are absent from
  `capabilities`; never fabricate. Keep the existing `capabilities` discipline.

---

## 6. Command surface

Add one command to `Cli__SG_Edge__Tui`, lazy-import + no-TTY fallback like the others:

```
sg edge tui control                 # local edge, actions live
sg edge tui control --target aws    # live edge read; actions greyed (pending Slice 5)
sg edge tui control --parent <zone> # override the zone
```

`sg edge tui` already aliases under `sg ed tui`. No new top-level surface; one
`add_typer` already wires `tui` into `sg edge`.

---

## 7. Testing (no mocks, pilot harness)

Follow the existing SG/Edge TUI test pattern (`@skipUnless` Textual importable; pure
layers always run):

- **Pure render** — the body markup builder is a pure function fed a hand-built snapshot;
  assert the action rows reflect `can_act()` (live vs greyed) and the preview text.
- **Pilot (`App.run_test()`)** against a **real** `Local_Source` on a temp `state_dir`
  (no mocks — same as the suite today):
  - `pilot.press('S')` → setup → assert snapshot now `deployed`, fleet=1.
  - type a slug into the `Input`, `pilot.press('n')` → assert the slug appears `live` in
    the DataTable and the Debug Panel logged the `register` call.
  - select the row, `pilot.press('g')` → assert the preview/outcome shows `welcome`.
  - `pilot.press('u')` → confirm modal → `y` → assert the slug is gone.
  - build with an **AWS source** (`Route53__AWS__Client__In_Memory`) → assert `can_act()`
    is `False`, action keys are greyed, and pressing `n` does **not** mutate (notify only).
  - head-less: assert the no-TTY path prints the card + the native-command footer and
    performs no mutation.

---

## 8. Slice sequence (bounded, one PR + debrief each)

| Slice | Scope |
|---|---|
| **C1 — converge + read** | Subclass `Tui__App`; `populate()` renders STATE (deployment summary + DataTable slugs + checks) from the shared snapshot; wire the shared `Debug__Event_Log`; carry `?`/`e`. No actions yet. Proves the convergence + the read. |
| **C2 — safe actions** | `request` (read-only, no gate) + `setup`; preview pane; Debug-Panel logging; `notify` feedback; `can_act()` greying for the AWS target. |
| **C3 — mutating actions + confirm** | `register` / `register --no-backend` / `unregister` / `teardown`; `ModalScreen` confirm for the destructive pair; `--dry-run` native preview if a register/teardown preview needs a CLI home. |
| **C-docs** | Update `library/guides/v0.2.38__sg-edge-tui-guide.md` (a Control Center section) + the `sg_edge/README.md` TUI table row + a per-slice debrief (what worked / what you'd reject — exploration discipline). |

Bounded effort, exploration stance (playbook §1): a day or so per slice; negative results
are a deliverable. If the two-column + DataTable shape proves cramped at the terminal
widths people use over the SSM chain, that finding is a win — capture it.

---

## 9. Acceptance criteria

1. `sg edge tui control` runs against the local edge; STATE shows infra + slugs + checks
   from real DNS; the DataTable cursor selects a slug.
2. From the screen you can `setup`, `register` (both modes), `request`, `unregister`, and
   `teardown` — each calling the same `Local__Edge__Stack` method as the matching
   `sg edge local` command (verify the Debug Panel shows the call).
3. Destructive actions (`unregister`, `teardown`) require a confirm; `request` is
   read-only with no gate.
4. `--target aws` shows real edge state with the action surface greyed + a "pending
   Slice 5" reason; no keypress raises.
5. Head-less prints the read-only card + the native-command footer and performs no
   mutation.
6. Built on `Tui__App` + the shared Debug Panel; pilot tests pass with a real source (no
   mocks); pure layers run on 3.11.
7. Every capability is reachable from the CLI (separation guide); the screen owns no logic.

---

## 10. Explicitly out of scope (seamed, not built)

- Live EC2 / cost / throughput / instance panes — Slice 5 of the v0.2.37 plan; they stay
  absent from `capabilities` and render "pending".
- AWS-target mutations — `AWS_Source.can_act()` stays `False` until Slice 5; the Control
  Center is forward-compatible (keys light up for free when it flips).
- A standalone canonical "everything" app — that is the sixth-conversation decision; the
  Control Center is the strongest *candidate* for it, not a pre-emption of it.
- Bench / lifecycle / request-tracer screens — separate proposals; the Control Center
  links to them later if they're promoted.
