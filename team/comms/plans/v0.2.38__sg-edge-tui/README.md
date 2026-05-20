---
title: "SG/Edge TUI — MVP implementation plan (codebase-grounded)"
version: v0.2.38
date: 2026-05-20
status: PLAN — no code yet. For human ratification before Dev picks up.
role: Dev / Architect
audience: implementing engineer (or next Claude thread) building the SG/Edge TUI
branch: claude/review-brief-tui-No5Rg
source-brief: v0.27.55__devbrief__sgedgerichtuiexperiments.md (Human, 17 May 2026)
related:
  - sg_compute_specs/sg_edge/README.md
  - sg_compute_specs/sg_edge/local/Local__Edge__Stack.py
  - sg_compute_specs/sg_edge/service/SG_Edge__DNS__Helper.py
  - sg_compute_specs/sg_edge/local/cli/Cli__SG_Edge__Local.py
  - team/comms/plans/v0.2.37__sg-edge/README.md
  - team/claude/debriefs/2026-05-20__v0.2.37-sg-edge-cli-and-local-deployment.md
decisions-confirmed:
  - "Data source: Local + stubbed AWS view (AWS reads real DNS; cost/rps/instance panes show a labelled pending state)"
  - "Module home: sg_compute_specs/sg_edge/tui/ sub-package"
  - "Sparklines/feed: real polling deltas only — no fabricated rps/cost"
  - "Framework: Textual + Rich"
---

# SG/Edge TUI — MVP implementation plan

> **PROPOSED — does not exist yet.** Nothing under `sg_compute_specs/sg_edge/tui/`
> exists at the time of writing. This plan describes what to build. Cross-check
> against the reality doc and `sg_compute_specs/sg_edge/README.md` as it lands.

---

## 1. Why this plan exists (and what it deliberately is not)

The 17-May dev brief proposes a visually-rich Textual TUI for SG/Edge: topology,
slug inventory, detail drill-in, live activity feed, sparklines, keyboard
actions, help overlay, ASCII export. The brief is an **aspiration written against
the full vision** of SG/Edge — live EC2 proxies, real request throughput, cost
per instance, wake events streaming in real time.

This plan re-grounds that vision on **what SG/Edge can actually produce today**,
because the project's non-negotiable rule is **no mocks, no fabrication**. A TUI
that draws a `$0.0012 cumulative` cost meter or a `12 rps` sparkline against data
that does not exist would be dishonest tooling. So the MVP renders only real,
queryable state, makes it feel alive through honest polling deltas, and leaves
clearly-labelled seams where the live-AWS data (Slice 5 of the v0.2.37 plan) will
slot in later without rework.

### The reality gap (what the brief mockup shows vs. what exists)

| Brief mockup element | Backing data today | MVP decision |
|---|---|---|
| Topology (browser → wildcard → fleet → slugs) | ✅ `Local__Edge__Stack.status()` / `SG_Edge__DNS__Helper` | **Build it** — this is the `sg edge local check` diagram, made live |
| Slug inventory + per-slug state | ✅ `Schema__Local__Edge__Slug` (`has_a`, `has_txt`, backend ip:port) | **Build it** |
| Checks / deviations panel | ✅ `Local__Edge__Stack.check()` issues | **Build it** |
| Proxy fleet membership | ✅ `proxies.<parent>` A record | **Build it** |
| Teardown counter (`zero_streak`) | ✅ `_state.<parent>` TXT | **Build it** |
| Live activity feed | ⚠ no event log exists — derive from polling deltas | **Build (honest)** — state-transition events only |
| Sparklines | ⚠ no time-series exists — derive from polling deltas | **Build (honest)** — slug/live counts over time, not rps |
| Cost (`$/min`, cumulative) | ❌ needs live EC2 + pricing — Slice 5 | **Defer** — labelled "pending Slice 5" pane |
| Request throughput / rps | ❌ needs proxy `slug_seen`/stats — Slice 5/6 | **Defer** — labelled pending pane |
| Instance id / uptime | ❌ needs EC2 launcher — Slice 5 | **Defer** — labelled pending pane |
| Wake-event history | ❌ needs Vault Waker (Phase 2) | **Defer** — labelled pending pane |
| Live actions: wake / terminate | ❌ needs EC2 wiring — Slice 5 | **Defer** — disabled keys with "pending" hint |

**Honest MVP scorecard: 8 of the 12 brief acceptance criteria genuinely met;
4 explicitly deferred behind labelled seams.** See §7.

---

## 2. Confirmed decisions (from the kickoff conversation)

1. **Data source = Local + stubbed AWS.** The TUI targets either the local stack
   (`edge.sg-labs.local`) or the live AWS edge (`edge.sg-labs.app`). The AWS
   source is **not empty** — the DNS registry (`proxies` / `_state` / `_sg.*`) is
   readable today via `SG_Edge__DNS__Helper` over `sg aws dns`. Only the
   cost/rps/instance/uptime panes carry no data on the AWS source yet; those
   render a **labelled pending state**, never fabricated numbers.
2. **Module home = `sg_compute_specs/sg_edge/tui/`** — a sub-package, separate
   from the primitives (which it must not modify) but co-located so it shares
   schemas, the test rig, and CI. Mirrors how `local/` and `cli/` already sit.
3. **Sparklines / activity feed = real polling deltas only.** The TUI observes
   successive snapshots and emits events on genuine state transitions; sparklines
   plot counts the TUI itself measured over time. No synthetic rps/cost.
4. **Framework = Textual + Rich.** The brief's pick; widget library (DataTable,
   Tree, Sparkline, RichLog), a real keyboard/focus model, and an async
   `run_test()` pilot harness that lets us test **without mocks**.

---

## 3. The key architectural idea: a normalised snapshot the TUI renders

The single most important design choice is to **keep the TUI thin over the
primitives** (brief AC#12; Risk #3 mitigation). We do that with one normalised
snapshot schema and a small data-source seam, exactly mirroring the existing
`_stack_factory` / `_dns_factory` injection pattern in the CLI.

```
                      ┌─────────────────────────────┐
   render-only        │   SG_Edge__TUI__App         │  Textual App (view layer)
   (Textual widgets)  │   widgets + key bindings    │
                      └──────────────┬──────────────┘
                                     │ reads
                      ┌──────────────▼──────────────┐
   pure data          │  Schema__SG_Edge__TUI__      │  one normalised snapshot
   (Type_Safe)        │  Snapshot                    │  (source-independent)
                      └──────────────▲──────────────┘
                                     │ produces
            ┌────────────────────────┴────────────────────────┐
            │                                                  │
 ┌──────────▼───────────┐                          ┌───────────▼──────────┐
 │ …__Local_Source      │                          │ …__AWS_Source        │
 │ wraps Local__Edge__   │                          │ wraps SG_Edge__DNS__  │
 │ Stack (file DNS)     │                          │ Helper (sg aws dns)  │
 └──────────────────────┘                          └──────────────────────┘
```

- **`Schema__SG_Edge__TUI__Snapshot`** (Type_Safe, pure data) — parent zone,
  deployed/zone/wildcard flags, fleet IPs, `zero_streak`, a list of normalised
  slugs (`slug`, `fqdn`, `state` enum, backend ip:port), the check issues, a
  capture timestamp, and a **`capabilities`** field per source (which panes have
  real data vs. pending).
- **`SG_Edge__TUI__Data_Source`** (interface) with `snapshot()` and the action
  methods (`register`, `unregister`, `request`, `teardown`). Two implementations:
  - `SG_Edge__TUI__Local_Source` — delegates straight to `Local__Edge__Stack`.
  - `SG_Edge__TUI__AWS_Source` — reads via `SG_Edge__DNS__Helper`; actions that
    need live EC2 (Slice 5) raise a typed `not-yet-wired` result the UI renders
    as a disabled hint rather than an error.
- **`SG_Edge__TUI__Differ`** (pure) — given previous and current snapshots, emits
  `Schema__SG_Edge__TUI__Event`s (slug registered / went-live / went-dormant /
  removed; fleet grew/shrank; issue appeared/cleared). Drives the activity feed.
- **`SG_Edge__TUI__Metrics`** (pure) — small in-memory ring buffers (deques) of
  `(timestamp, value)` for honest series: total slugs, live slugs, fleet size.
  Sparklines render these. **No rps/cost** — those are not measurable here.

Why this matters: when Slice 5 lands real EC2/cost data, we add fields to the
snapshot and fill them in `…__AWS_Source` only. The view layer and the local
source are untouched. The "pending" panes light up automatically.

---

## 4. Convention boundary: Type_Safe data vs. Textual view classes

CLAUDE.md rule #1 ("all classes extend `Type_Safe`") governs **our domain
layer**. Framework-mandated base classes are the documented carve-out — exactly
as routes subclass `Fast_API__Routes` and `Cli__SG_Edge__Local.serve` subclasses
`http.server.BaseHTTPRequestHandler`. For the TUI:

- **Data / schema / enum / source / differ / metrics layer** → `Type_Safe`,
  zero raw-primitive attributes, `Enum__*` for fixed sets, one class per file,
  empty `__init__.py`, 80-char headers, no docstrings. **This is where the logic
  and the tests live.**
- **View layer** (`SG_Edge__TUI__App` and widgets) → subclasses Textual's `App`,
  `Widget`, `Static`, `DataTable`, etc. Framework carve-out. **Routes-have-no-
  logic discipline applies**: widgets render the snapshot and dispatch key
  presses to the data source; they hold no business logic.

This split is also what makes the no-mocks testing work: the testable logic is
all in the Type_Safe layer, and the thin view layer is exercised through
Textual's pilot.

---

## 5. Package layout

```
sg_compute_specs/sg_edge/tui/
  sg_edge_tui__config.py        refresh interval, default target, theme, ring-buffer size
  enums/
    Enum__SG_Edge__TUI__Target          (LOCAL / AWS)
    Enum__SG_Edge__TUI__Slug_State      (LIVE / DORMANT / ORPHAN_BACKEND)
    Enum__SG_Edge__TUI__Event_Kind      (SLUG_REGISTERED / WENT_LIVE / WENT_DORMANT / REMOVED / FLEET_CHANGED / ISSUE / CLEARED)
    Enum__SG_Edge__TUI__Capability      (TOPOLOGY / SLUGS / CHECKS / FLEET / COST / THROUGHPUT / INSTANCES)  # last 3 = pending
  schemas/
    Schema__SG_Edge__TUI__Slug          (slug, fqdn, state, backend_ip, backend_port)
    Schema__SG_Edge__TUI__Event         (kind, slug, detail, ts)
    Schema__SG_Edge__TUI__Series_Point  (ts, value)
    Schema__SG_Edge__TUI__Snapshot      (parent, deployed, zone_exists, wildcard, fleet_ips,
                                         zero_streak, slugs, issues, capabilities, captured_at)
    List__SG_Edge__TUI__{Slug,Event,Series_Point}
  source/
    SG_Edge__TUI__Data_Source           interface (snapshot + actions)
    SG_Edge__TUI__Local_Source          wraps Local__Edge__Stack
    SG_Edge__TUI__AWS_Source            wraps SG_Edge__DNS__Helper (read) + Slice-5 action seams
  service/
    SG_Edge__TUI__Differ                pure: (prev, curr) → events
    SG_Edge__TUI__Metrics               pure: ring buffers → series for sparklines
    SG_Edge__TUI__Card                  pure: snapshot → ASCII export string (reuses check layout)
  app/
    SG_Edge__TUI__App                   textual.App — bindings, timer refresh, layout
    widgets/                            Topology, SlugTable, Detail, ActivityFeed, Sparklines, Checks
    screens/                            Help (ModalScreen)
  cli/
    Cli__SG_Edge__Tui                   `sg edge tui` typer sub-app (run / diagnose / export)
  tests/                               co-located, no mocks (pilot + in-memory sources)
```

One external touch, same minimal pattern as the rest of SG/Edge: a single
`add_typer(tui, …)` line in `cli/Cli__SG_Edge.py`. Nothing else imports `tui`.

---

## 6. Slice sequence (MVP)

| Slice | Scope | Textual? | Runs on 3.11? |
|---|---|---|---|
| **T1 — data layer** | snapshot schema + enums; `Local_Source` (over `Local__Edge__Stack`) + `AWS_Source` (over `SG_Edge__DNS__Helper`, `Route53__AWS__Client__In_Memory` in tests); `Differ` + `Metrics`, both pure. Full unit coverage, no Textual. | no | **yes** |
| **T2 — static app shell** | `SG_Edge__TUI__App` + layout: Topology, SlugTable (DataTable), Detail, Checks. Renders one snapshot. Keyboard nav (`Tab` panes, arrows in table, `Enter`/selection → Detail). Tested via `run_test()` pilot. | yes | no (gated) |
| **T3 — live + feed + sparklines** | timer poll at config interval (default 4 Hz; see §8); `Differ`-driven ActivityFeed (RichLog); honest Sparklines from `Metrics`. Diff highlight on changed rows. | yes | no (gated) |
| **T4 — actions** | wire `r`egister / `u`nregister / `x` request-simulate / `R`efresh / `D`estroy(teardown, confirmed) to the source. AWS-only live actions (wake/terminate) render as disabled keys with a "pending Slice 5" hint. | yes | partial |
| **T5 — help + export + theme** | `?` Help overlay (context-aware bindings); `c` export ASCII card (reuses `SG_Edge__TUI__Card`, writes to file + clipboard-if-available); dark theme default, `t` toggles. | yes | no (gated) |
| **T6 — deployment chain + docs** | `sg edge tui diagnose` ($TERM/$LANG/colors/unicode/truecolor checks from the brief addendum); Dockerfile `ENV LANG/LC_ALL/TERM` + `ncurses-term locales`; graceful degradation (no-TTY → single static `check`-style render); user-guide section + reality-doc update. | yes | no (gated) |

**Note on key choices.** The brief assigns `r` to "export card". We have more
actions than the brief mockup (register/unregister/request), so this plan uses
`c` for the card export and frees `r` for `r`egister, with the full map shown in
the `?` overlay. Final bindings are a polish-time call; the Help overlay is the
source of truth either way.

---

## 7. Acceptance-criteria mapping (brief §Acceptance Criteria)

| # | Brief criterion | MVP status |
|---|---|---|
| 1 | Framework selected (Textual + Rich) | ✅ confirmed §2 |
| 2 | New dedicated module | ✅ `sg_compute_specs/sg_edge/tui/` |
| 3 | Topology view, live component status | ✅ T2/T3 |
| 4 | Slug inventory, real, updates live | ✅ T2/T3 |
| 5 | Detail view (instance, vault, cost) | 🟡 **partial** — vault/backend ✅; instance/cost = pending Slice 5 |
| 6 | Live activity feed (wake/request/error) | 🟡 **honest subset** — state-transition events ✅; wake/request events need Slice 5/Phase 2 |
| 7 | Sparkline panels (throughput trends) | 🟡 **honest subset** — slug/live/fleet counts ✅; throughput = pending Slice 6 |
| 8 | Keyboard navigation, no mouse required | ✅ T2/T4 |
| 9 | Help overlay (`?`), context-aware | ✅ T5 |
| 10 | ASCII export (shareable card) | ✅ T5 |
| 11 | Graceful degradation, ≥3 terminals | ✅ T6 (no-TTY fallback + diagnose); manual terminal matrix |
| 12 | Sits on primitives without modifying them | ✅ — snapshot seam; only touch is one `add_typer` line |

Deferred-but-seamed (light up when v0.2.37 Slice 5/6 land): cost, throughput,
instance id/uptime, wake-event history, live wake/terminate actions.

---

## 8. Deployment-chain notes (brief addendum — folded in, not bolted on)

The TUI is reached through laptop → SSH/SSM → `docker exec -it` → container. Two
cheap, durable wins from the addendum belong in this MVP:

- **`sg edge tui diagnose`** — prints `$TERM`, `$LANG`, `tput colors`, a unicode
  block-render test, and a truecolor probe, so an operator can self-check before
  reporting "the box-drawing looks broken".
- **Dockerfile env** — `ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 TERM=xterm-256color` and
  `RUN apt-get install -y ncurses-term locales && locale-gen C.UTF-8`. Set once,
  pays off every session. (Coordinate with DevOps on the service image.)

Two design constraints follow:

- **Throttle refresh to ~4 Hz** (config-driven). Every redraw is bytes over the
  SSH stream; 60 FPS is pointless for DNS-grounded operational data and unkind to
  flaky links. Textual diffs partial redraws, but the *poll* cadence is ours.
- **Graceful degradation** — if stdout is not a TTY or `$TERM=dumb`, do not start
  the full app; fall back to a one-shot static `check`-style render and exit
  cleanly (this also keeps `sg edge tui` safe to pipe / run in CI).

---

## 9. Testing (no mocks, no patches)

- **Data layer (T1)** — `Local_Source` tested against a real `Local__Edge__Stack`
  in an isolated temp `state_dir` (the local-stack tests already prove this is
  fast and deterministic). `AWS_Source` tested against
  `Route53__AWS__Client__In_Memory` injected into `SG_Edge__DNS__Helper`. `Differ`
  and `Metrics` are pure — fed hand-built snapshot sequences, asserted on emitted
  events / series. All of this runs on **3.11**.
- **View layer (T2–T5)** — Textual's async `App.run_test()` pilot: push keys
  (`pilot.press("tab", "down", "enter")`), assert on widget/DOM state and on the
  source the app was constructed with. **Sources are real in-memory
  implementations**, not mocks — same philosophy as the `_stack_factory` seam.
- **Gating** — Textual is **not installed in this container** (neither are
  typer/rich today). The view-layer suite `@skipUnless` Textual is importable,
  exactly as the CLI suite gates on typer. The T1 data-layer suite has no Textual
  dependency and always runs.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Fabrication creep** — pressure to fill empty AWS panes with plausible numbers | The `capabilities` field makes "no data yet" a first-class, rendered state. Code review rule: a sparkline/metric must trace to a `Metrics` series the TUI measured, or a snapshot field a source actually read. |
| **Type_Safe vs. Textual base classes** | Explicit carve-out (§4) with in-package precedent (`serve` subclasses `BaseHTTPRequestHandler`). Logic stays in the Type_Safe layer; widgets stay thin. |
| **New heavy dependency (Textual)** | Confined to the view layer + gated tests. The data layer (the valuable, reusable part) has zero Textual dependency and runs on 3.11. |
| **TUI drifts from primitives (brief Risk #3)** | The snapshot seam *is* the subscription-to-primitive-output the brief asks for. The TUI holds no parallel state; every frame is re-derived from a source read. |
| **Terminal compatibility (brief Risk #2)** | `diagnose` subcommand + no-TTY fallback + a manual 3-terminal check (iTerm2 / Wezterm / Windows Terminal) in T6. |

---

## 11. Effort & sequencing

The brief estimates 2–3 weeks for the full v1 (delight included). This **MVP**
(slices T1–T5, with T6 as a fast follow) is a smaller, honest cut: a real,
demoable, keyboard-driven dashboard over the local + DNS-grounded AWS state,
with the live-AWS panes seamed for later. T1 is the foundation and is worth
landing and reviewing on its own (pure, 3.11, no new deps) before any Textual
code is written.

Suggested order: **T1 → T2 → T3 → T4 → T5 → T6**, one commit (or small PR) per
slice, each with its debrief under `team/claude/debriefs/` per CLAUDE.md §26.

---

## 12. Open questions for the human

1. **AWS target default zone** — confirm `edge.sg-labs.app` (the hard-coded edge
   parent) is the right read-only target for the AWS source pre-Slice-5.
2. **Card export destination** — file only, or also attempt clipboard
   (`pbcopy`/`wl-copy`/OSC-52) when available? OSC-52 survives SSH and is the
   most chain-friendly; proposed default.
3. **Where the user guide lives** — extend `library/guides/v0.2.36__sg-edge-local-user-guide.md`
   with a TUI section, or a new `v0.2.38__sg-edge-tui-guide.md`? Proposed: new file.
4. **Theme** — dark default confirmed by the brief; ship light as `t`-toggle in
   MVP or defer? Proposed: ship the toggle, it's cheap with Textual.
