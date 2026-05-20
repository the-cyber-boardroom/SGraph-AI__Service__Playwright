---
title: "SG/Edge TUI — exploration MVP plan (five screens, codebase-grounded)"
version: v0.2.38
date: 2026-05-20
status: PLAN — no code yet. For human ratification before Dev picks up.
role: Dev / Architect
audience: implementing engineer (or next Claude thread) building the SG/Edge TUI
branch: claude/review-brief-tui-No5Rg
source-briefs:
  - v0.27.55__devbrief__sgedgerichtuiexperiments.md       (framing — framework, deployment chain)
  - v0.27.55__devbrief__sgedgetuifirstfivescreens.md      (this plan's concrete subject — five first screens)
related:
  - sg_compute_specs/sg_edge/README.md
  - sg_compute_specs/sg_edge/local/Local__Edge__Stack.py
  - sg_compute_specs/sg_edge/service/SG_Edge__DNS__Helper.py
  - sg_compute_specs/sg_edge/local/cli/Cli__SG_Edge__Local.py
  - team/comms/plans/v0.2.37__sg-edge/README.md
  - team/claude/debriefs/2026-05-20__v0.2.37-sg-edge-cli-and-local-deployment.md
decisions-confirmed:
  - "Approach: explore-first — five standalone exploratory screens over a shared data layer; the single composite dashboard is the deferred 'canonical' target (sixth conversation decides what gets promoted)"
  - "Data source: Local + stubbed AWS (AWS reads real DNS; cost/rps/instance panes show a labelled pending state)"
  - "Module home: sg_compute_specs/sg_edge/tui/ sub-package"
  - "Sparklines/feed: real polling deltas only — no fabricated rps/cost"
  - "Framework: Textual + Rich"
  - "AWS target zone: edge.sg-labs.app (the hard-coded edge parent)"
  - "Card export: file + OSC-52 clipboard (survives the SSH/SSM chain)"
  - "User guide: new file library/guides/v0.2.38__sg-edge-tui-guide.md"
  - "Theme: dark default, ship a light-mode toggle in MVP"
---

# SG/Edge TUI — exploration MVP plan (five screens)

> **PROPOSED — does not exist yet.** Nothing under `sg_compute_specs/sg_edge/tui/`
> exists at the time of writing. This plan describes what to build. Cross-check
> against the reality doc and `sg_compute_specs/sg_edge/README.md` as it lands.

---

## 1. Why this plan exists (and what changed)

Two dev briefs from 17 May frame this work:

- The **framing brief** picked the framework (Textual + Rich), the de-commoditising
  rationale, and the SSH/SSM + `docker exec` deployment chain.
- The **five-screens brief** is this plan's concrete subject. It deliberately
  re-frames the work as **exploration, not production**: build five standalone
  exploratory screens, learn which visual idioms work, *then* a sixth conversation
  decides which patterns get promoted into a canonical SG/Edge dashboard. It is
  explicit: "these are explorations; the canonical TUI comes after."

So the build order inverts from a first reading: **explore (5 screens) → decide →
build canonical.** The single composite dashboard sketched in the framing brief
becomes the *deferred* target (§12), not the immediate one.

The project's non-negotiable rule still governs everything: **no mocks, no
fabrication.** Both briefs' mockups are dense with data that does not exist yet
(instance IDs, uptime, `$/min` cost, rps/latency sparklines, a live request feed).
A screen that draws those against absent data would be dishonest tooling. The MVP
renders only real, queryable state and leaves clearly-labelled seams where the
live-AWS data (Slice 5 of the v0.2.37 plan) and the observability event source
will slot in later. Per the five-screens brief, **documenting what we tried and
rejected — the negative results — is an explicit deliverable.**

---

## 2. Confirmed decisions

1. **Explore-first, five screens.** Standalone commands over a shared data layer;
   canonical composite app deferred (§12).
2. **Data source = Local + stubbed AWS.** Target the local stack
   (`edge.sg-labs.local`) or the live AWS edge (`edge.sg-labs.app`). The AWS source
   is **not empty** — the DNS registry (`proxies` / `_state` / `_sg.*`) is readable
   today via `SG_Edge__DNS__Helper`. Only cost/rps/instance/uptime carry no data
   yet; those render a **labelled pending state**, never fabricated numbers.
3. **Module home = `sg_compute_specs/sg_edge/tui/`** — a sub-package, separate from
   the primitives (which it must not modify) but co-located. Mirrors `local/`, `cli/`.
4. **Sparklines / activity feed = real polling deltas only.** Series are counts the
   TUI itself measured over successive snapshots; events are genuine state
   transitions. No synthetic rps/cost.
5. **Framework = Textual + Rich.**
6. **AWS target zone = `edge.sg-labs.app`** (the hard-coded edge parent).
7. **Card export = file + OSC-52 clipboard** (OSC-52 survives the SSH/SSM chain).
8. **User guide = new file** `library/guides/v0.2.38__sg-edge-tui-guide.md`.
9. **Theme = dark default + light-mode toggle (`t`)** shipped in MVP.

---

## 3. The shared foundation: one normalised snapshot the screens render

The most important design choice: **all five screens read from one shared data
layer**, so the TUI stays thin over the primitives (framing-brief AC#12; Risk #3
mitigation) and the same layer feeds the eventual canonical app. We use a single
snapshot schema plus a small data-source seam, mirroring the existing
`_stack_factory` / `_dns_factory` injection pattern in the CLI.

```
   five screen apps (view layer, Textual)
        │  each reads
        ▼
   Schema__SG_Edge__TUI__Snapshot         one normalised snapshot (source-independent)
        ▲  produced by
        │
   ┌────┴─────────────┐         ┌──────────────────────┐
   │ …__Local_Source  │         │ …__AWS_Source        │
   │ Local__Edge__Stack│         │ SG_Edge__DNS__Helper │
   │ (file DNS)       │         │ (sg aws dns)         │
   └──────────────────┘         └──────────────────────┘
```

- **`Schema__SG_Edge__TUI__Snapshot`** (Type_Safe, pure data) — parent zone,
  deployed/zone/wildcard flags, fleet IPs, `zero_streak`, normalised slugs
  (`slug`, `fqdn`, `state` enum, backend ip:port), check issues, a capture
  timestamp, and a **`capabilities`** field (which panes have real data vs pending).
- **`SG_Edge__TUI__Data_Source`** (interface) — `snapshot()` plus action methods
  (`register`, `unregister`, `request`, `teardown`). Two implementations:
  - `…__Local_Source` — delegates to `Local__Edge__Stack`.
  - `…__AWS_Source` — reads via `SG_Edge__DNS__Helper`; actions needing live EC2
    (Slice 5) return a typed `not-yet-wired` result the UI renders as a disabled
    hint, not an error.
- **`SG_Edge__TUI__Differ`** (pure) — `(prev, curr)` → `Schema__SG_Edge__TUI__Event`s
  (slug registered / went-live / went-dormant / removed; fleet grew/shrank; issue
  appeared/cleared). Drives the **event stream** (Screen 5) honestly.
- **`SG_Edge__TUI__Metrics`** (pure) — small ring buffers (deques) of
  `(timestamp, value)` for honest series: total slugs, live slugs, fleet size.
  Sparklines render these. **No rps/cost** — not measurable here.
- **`SG_Edge__TUI__Comparison`** (pure) — diffs a local snapshot against an AWS
  snapshot for **Screen 3** (per-row in-sync / local-only / edge-only). Honest
  *two-way*; the version-drift matrix is out of `sg_edge`'s data reach (see §6).

Why this matters: when Slice 5 lands real EC2/cost data, we add snapshot fields
and fill them in `…__AWS_Source` only. The screens and the local source are
untouched; the "pending" panes light up automatically.

---

## 4. Convention boundary: Type_Safe data vs. Textual view classes

CLAUDE.md rule #1 ("all classes extend `Type_Safe`") governs the **domain layer**.
Framework-mandated base classes are the documented carve-out — as routes subclass
`Fast_API__Routes` and `Cli__SG_Edge__Local.serve` subclasses
`http.server.BaseHTTPRequestHandler`. For the TUI:

- **Data / schema / enum / source / differ / metrics / comparison / card layer** →
  `Type_Safe`, zero raw-primitive attributes, `Enum__*` for fixed sets, one class
  per file, empty `__init__.py`, 80-char headers, no docstrings. **All logic and
  tests live here.**
- **View layer** (the five screen apps + widgets) → subclasses Textual's `App`,
  `Widget`, `Static`, `DataTable`, etc. Framework carve-out. The
  routes-have-no-logic discipline applies: widgets render the snapshot and dispatch
  key presses to the data source; they hold no business logic.

---

## 5. Package layout

```
sg_compute_specs/sg_edge/tui/
  sg_edge_tui__config.py        refresh interval, default target, theme, ring-buffer size, OSC-52 toggle
  enums/
    Enum__SG_Edge__TUI__Target          (LOCAL / AWS)
    Enum__SG_Edge__TUI__Slug_State      (LIVE / DORMANT / ORPHAN_BACKEND)
    Enum__SG_Edge__TUI__Event_Kind      (SLUG_REGISTERED / WENT_LIVE / WENT_DORMANT / REMOVED / FLEET_CHANGED / ISSUE / CLEARED)
    Enum__SG_Edge__TUI__Capability      (TOPOLOGY / SLUGS / CHECKS / FLEET / COST / THROUGHPUT / INSTANCES)  # last 3 pending
    Enum__SG_Edge__TUI__Sync_State      (IN_SYNC / LOCAL_ONLY / EDGE_ONLY)            # Screen 3
  schemas/
    Schema__SG_Edge__TUI__Slug          (slug, fqdn, state, backend_ip, backend_port)
    Schema__SG_Edge__TUI__Event         (kind, slug, detail, ts)
    Schema__SG_Edge__TUI__Series_Point  (ts, value)
    Schema__SG_Edge__TUI__Snapshot      (parent, deployed, zone_exists, wildcard, fleet_ips,
                                         zero_streak, slugs, issues, capabilities, captured_at)
    Schema__SG_Edge__TUI__Comparison_Row(name, local_present, edge_present, sync_state)   # Screen 3
    List__SG_Edge__TUI__{Slug,Event,Series_Point,Comparison_Row}
  source/
    SG_Edge__TUI__Data_Source           interface (snapshot + actions)
    SG_Edge__TUI__Local_Source          wraps Local__Edge__Stack
    SG_Edge__TUI__AWS_Source            wraps SG_Edge__DNS__Helper (read) + Slice-5 action seams
  service/
    SG_Edge__TUI__Differ                pure: (prev, curr) → events
    SG_Edge__TUI__Metrics               pure: ring buffers → series for sparklines
    SG_Edge__TUI__Comparison            pure: (local, aws) snapshots → comparison rows
    SG_Edge__TUI__Card                  pure: snapshot → ASCII export string (reuses check layout)
  screens/                              one Textual App per exploratory screen
    SG_Edge__TUI__Screen__Deployment    Screen 1
    SG_Edge__TUI__Screen__Topology      Screen 2
    SG_Edge__TUI__Screen__Compare       Screen 3
    SG_Edge__TUI__Screen__Slug_Detail   Screen 4
    SG_Edge__TUI__Screen__Events        Screen 5
    widgets/                            shared: StatusGlyph, Sparkline, KeyBar, Help (ModalScreen)
  cli/
    Cli__SG_Edge__Tui                   `sg edge tui {deployment|topology|compare|slug|events}` + diagnose + export
  tests/                               co-located, no mocks (pilot + in-memory sources)
```

One external touch, same minimal pattern as the rest of SG/Edge: a single
`add_typer(tui, …)` line in `cli/Cli__SG_Edge.py`. Nothing else imports `tui`. The
five screens are independent commands → runnable side-by-side in tmux (five-screens
brief open-Q), which falls out for free.

---

## 6. The five exploratory screens — reality-grounded

What each screen can show **truthfully today** vs. what is a labelled-pending seam:

| Screen | Real today | Pending (Slice 5 / Phase 2 / observability) | Verdict |
|---|---|---|---|
| **1. Deployment Reality** | wildcard, fleet IPs, DNS record counts, registered slugs + state | proxy EC2 rows (`i-…`, AZ, uptime), vault-srv instances + "vaults loaded", live CF/Lambda ARNs | **Buildable** — real infra + slug rows; instance rows seamed |
| **2. Topology** | the layered shape (browser → wildcard → fleet → slugs) = the `check` diagram, interactive | per-proxy instances, vault-server grouping, "active flows" sparkline | **Buildable** — honest topology; richer nodes seamed |
| **3. Local vs Edge** | local zone vs AWS edge zone: slug / fleet / wildcard / record presence — fully comparable via the two sources | a distinct "Deployed" 3rd column; component **version** drift (lives in other services, not `sg_edge`) | **Sweet spot** — honest *two-way* drift; three-way version matrix out of reach |
| **4. Slug Detail** | slug, fqdn, A/TXT state, backend ip:port, the DNS A/TXT records | instance (id/type/AZ/IP/health), cost, rps/error/latency sparklines, source/article/working vault bindings | **Honest skeleton** — State + DNS real; rest seamed |
| **5. Live Event Stream** | state-transition events from polling deltas (registered / went-live / removed / fleet / issue) — the Differ already produces these | per-request events + latencies + wake events (needs the observability session / Slice 5/6) | **Honest trickle**, not a fast request stream |

Two callouts:

- **Screen 3 is the happy alignment.** The five-screens brief names it the most
  operationally valuable, and it is one of the *most* honestly buildable — because
  local and edge are both real sources right now. Invest here. The only
  out-of-reach part is the per-component version matrix (that data is not in
  `sg_edge`); the slug/fleet/config presence comparison is fully real.
- **Screens 1/2/3 are rich with real data and exercise the three most distinct
  idioms** (grouped list / topology art / comparison table). **4 and 5 are thinner
  today** — but building them as honest skeletons is itself a valuable exploration
  result: it visibly shows the gap Slice 5 / observability will fill.

**Sequence by real-data-richness (fastest learning first): 1 → 3 → 2 → 4 → 5.**

The sketches in the brief are starting points, not specifications — the brief is
explicit that the agent may deviate, and that "explore the art of the possible" is
the actual brief. Each screen ships with a short *what worked / what I'd reject*
note.

---

## 7. Slice sequence (MVP)

| Slice | Scope | Textual? | Runs on 3.11? |
|---|---|---|---|
| **T1 — shared data layer** | snapshot schema + enums; `Local_Source` + `AWS_Source` (tests inject `Route53__AWS__Client__In_Memory`); `Differ`, `Metrics`, `Comparison`, `Card` — all pure. Full unit coverage, no Textual. **Land + review on its own.** | no | **yes** |
| **S1 — Deployment Reality** | grouped panes (edge infra / fleet / slugs); status glyphs; periodic refresh; instance rows render labelled-pending. | yes | no (gated) |
| **S3 — Local vs Edge** | two-source comparison table via `Comparison`; per-row sync glyph; drift summary line; version matrix shown as explicit "out of scope (other services)". | yes | no (gated) |
| **S2 — Topology** | ASCII-art layered graph (the `check` diagram, interactive); keyboard focus between nodes; `Enter` on a slug node → opens S4. | yes | no (gated) |
| **S4 — Slug Detail** | drill-in; State + DNS sections real; Instance / Cost / Activity / Vault-binding sections labelled-pending; `Esc` back. | yes | no (gated) |
| **S5 — Live Event Stream** | `Differ`-driven feed (RichLog), newest-on-top; filter shortcuts; `Space` pause; honest sparklines from `Metrics`. | yes | no (gated) |
| **T-chain — deployment chain + docs** | `sg edge tui diagnose`; Dockerfile `ENV LANG/LC_ALL/TERM` + `ncurses-term locales`; no-TTY fallback (one-shot static render); `<100ms` first frame; resize re-layout; `library/guides/v0.2.38__sg-edge-tui-guide.md`; reality-doc update. | yes | no (gated) |

Shared widgets (StatusGlyph, Sparkline, KeyBar, Help overlay, theme toggle, OSC-52
card export) are built alongside S1 and reused across S2–S5.

---

## 8. Acceptance-criteria mapping (five-screens brief §Acceptance Criteria)

| # | Criterion | MVP status |
|---|---|---|
| 1 | Five screens buildable and runnable | ✅ S1–S5 as `sg edge tui *` commands |
| 2 | Screen 1 shows current state at a glance | ✅ real infra + slugs; instance rows seamed |
| 3 | Screen 2 topology readable | ✅ |
| 4 | Screen 3 surfaces drift | 🟡 honest **two-way** (local vs edge); version matrix out of `sg_edge`'s reach |
| 5 | Screen 4 drill-in via keyboard | 🟡 skeleton — State+DNS real; Instance/Cost/Activity seamed |
| 6 | Screen 5 updates in real time | 🟡 honest state-transition trickle; request stream pending observability/Slice 5/6 |
| 7 | Run cleanly over SSM + docker exec | ✅ T-chain slice (manual verify in real chain) |
| 8 | First frame < 100ms | ✅ render empty/cached snapshot immediately; first poll async |
| 9 | Notes per screen on what worked / did not | ✅ debrief per screen (good-failure convention) |
| 10 | Retrospective after ~1 week of use | process item — the "sixth conversation" → §12 |

Deferred-but-seamed (light up when v0.2.37 Slice 5/6 + observability land): cost,
throughput, instance id/uptime, wake/request event feed, live wake/terminate, the
"Deployed" third environment + version matrix.

---

## 9. Deployment-chain notes (framing-brief addendum — folded in)

Reached through laptop → SSH/SSM → `docker exec -it` → container. Build into MVP:

- **`sg edge tui diagnose`** — prints `$TERM`, `$LANG`, `tput colors`, a unicode
  block-render test, a truecolor probe. Operator self-check before reporting
  broken box-drawing.
- **Dockerfile env** — `ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 TERM=xterm-256color` +
  `RUN apt-get install -y ncurses-term locales && locale-gen C.UTF-8`. Coordinate
  with DevOps on the service image.

Design constraints that follow:

- **Throttle refresh to 5–10 Hz** (config-driven; default ~4 Hz). Every redraw is
  bytes over SSH; 60 FPS is pointless for DNS-grounded data and unkind to flaky links.
- **First frame < 100ms** — render an empty/cached snapshot immediately, run the
  first poll async, fill in when it returns.
- **Reset on resize** — re-layout cleanly; no broken frames.
- **No mouse required** — every action reachable via keyboard.
- **Graceful degradation** — non-TTY / `$TERM=dumb` → one-shot static `check`-style
  render and clean exit (keeps `sg edge tui` safe to pipe / run in CI).

---

## 10. Testing (no mocks, no patches)

- **Data layer (T1)** — `Local_Source` against a real `Local__Edge__Stack` in an
  isolated temp `state_dir`; `AWS_Source` against `Route53__AWS__Client__In_Memory`
  injected into `SG_Edge__DNS__Helper`. `Differ` / `Metrics` / `Comparison` / `Card`
  are pure — fed hand-built snapshot sequences, asserted on outputs. Runs on **3.11**.
- **View layer (S1–S5)** — Textual's async `App.run_test()` pilot: push keys
  (`pilot.press("tab", "down", "enter")`), assert on widget/DOM state and on the
  real in-memory source the app was built with. **No mocks** — same philosophy as
  the `_stack_factory` seam.
- **Gating** — Textual is **not installed in this container** (neither are
  typer/rich today). The view-layer suite `@skipUnless` Textual is importable,
  exactly as the CLI suite gates on typer. The T1 data-layer suite always runs.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Fabrication creep** — filling empty AWS/instance/cost panes with plausible numbers | The `capabilities` field makes "no data yet" a first-class rendered state. Review rule: every metric must trace to a `Metrics` series or a snapshot field a source actually read. |
| **Type_Safe vs. Textual base classes** | Explicit carve-out (§4) with in-package precedent. Logic in the Type_Safe layer; widgets thin. |
| **New heavy dependency (Textual)** | Confined to the view layer + gated tests. The valuable, reusable data layer (T1) has zero Textual dependency and runs on 3.11. |
| **TUI drifts from primitives (framing-brief Risk #3)** | The snapshot seam *is* the subscription-to-primitive-output the brief asks for. No parallel state; every frame is re-derived from a source read. |
| **Terminal compatibility (framing-brief Risk #2)** | `diagnose` + no-TTY fallback + a manual 3-terminal check (iTerm2 / Wezterm / Windows Terminal). |
| **Exploration churn** | By design — the five-screens brief expects some screens discarded. Bounded effort per screen; negative results are a deliverable, not a failure. |

---

## 12. Effort, sequencing, and the deferred canonical app

- **T1** ~1–2 days (pure, 3.11, no new deps) — land and review **first**.
- **Five screens** ~5–7 days total per the brief (1–2 days each, bounded), built
  in the order **1 → 3 → 2 → 4 → 5**, one commit/small-PR + debrief per screen.
- **T-chain + docs** — fast follow.

**Deferred to the "sixth conversation" (post-exploration):** the single composite
dashboard from the framing brief (topology + slug table + detail + activity in one
app — what an earlier draft of this plan called T2–T5). After ~1 week of using the
five screens, we decide which patterns get promoted: tabs of one app, a reduced
set, or a redesign absorbing the best of each. T1 already feeds whatever wins.

---

## 13. Open questions for the human

1. **Screen 5 event source** — for the MVP it's the T1 `Differ` (honest
   state-transition trickle). The brief suggests the unified observability session
   as the eventual source. Confirm: MVP stays on the Differ, observability is a
   later swap?
2. **Screen 3 "Deployed" column** — MVP does **local vs edge** only (the two real
   sources). Is a third "Deployed" column meaningful for `sg_edge` specifically, or
   is that a cross-service concern that belongs to the labs/admin UI instead?
3. **Command surface** — `sg edge tui <screen>` subcommands (proposed) vs. the
   brief's flat `sg-edge-tui-<name>`. Subcommands keep the `sg edge` tree tidy and
   still run side-by-side in tmux. Confirm subcommands?
