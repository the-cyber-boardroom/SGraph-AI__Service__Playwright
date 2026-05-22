---
title: "SG/Edge Cockpit — embedding the chat as a left column (talk to your edge)"
version: v0.2.40
date: 2026-05-21
status: PLAN — no code yet. UI/UX mockups + build slices for human ratification.
role: Architect → Dev
audience: the dev agent extending sg_compute_specs/sg_edge/tui/
builds-on:
  - library/guides/v0.2.39__tui_cli_separation.md                              # a TUI is a GUI over the CLI
  - team/humans/dinis_cruz/claude-code-web/05/21/14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md
  - sgraph_ai_service_playwright__cli/tui/tool_api/                            # the BUILT execution center / registry / provider base
  - sgraph_ai_service_playwright__cli/aws/s3/tui_api/S3__Tui_Api__Provider.py  # the provider template to mirror
  - sgraph_ai_service_playwright__cli/aws/bedrock/tui/service/Bedrock__Chat__Engine.py  # send_turn_agentic (the tool loop)
  - sgraph_ai_service_playwright__cli/aws/bedrock/tui/screens/widgets/         # Chat__Bubble/Composer/Cost__Meter/Inspector
  - sg_compute_specs/sg_edge/tui/screens/SG_Edge__TUI__Screen__Control_Center.py  # the host screen we extend
  - sg_compute_specs/sg_edge/tui/source/SG_Edge__TUI__Data_Source.py           # the action seam dispatch reuses
related:
  - team/comms/plans/v0.2.39__sg-edge-tui-control-center/README.md
---

# SG/Edge Cockpit — chat as a left column

> **What this is.** Put a **conversational agent column on the left of the SG/Edge
> Control Center** so you can *talk to your local edge* — "set up the edge, register
> alice, is she live?" — while the live state, the manual action keys, and the Debug
> Panel sit to its right. The chat drives the **same backend** the keys and the
> `sg edge local *` CLI drive (separation guide): one edge, three ways to operate it
> (type a sentence · press a key · run a command), all visible in one screen.
>
> **Why it's mostly assembly.** The hard parts already exist on this branch: the
> `cli/tui/tool_api/` framework (registry · execution center · scopes · dry-run/confirm
> · audit · cost), the agentic chat loop (`Bedrock__Chat__Engine.send_turn_agentic`),
> the chat widgets, and my Control Center (the state read + the action seam). The new
> code is **one provider** + **one host screen that composes existing widgets**.

---

## 1. What exists vs. what's new (honesty)

| Piece | Status | Where |
|---|---|---|
| Tool-API framework: `Registry`, `Execution_Center`, `Provider` base, tokens, loadout, preconditions, audit, cost | ✅ **built** | `cli/tui/tool_api/` |
| Reference provider (the template) | ✅ **built** | `aws/s3/tui_api/S3__Tui_Api__Provider` (~95 lines) |
| Agentic chat loop (Converse tool-use; per-turn cost = model + tools; Inspector) | ✅ **built** | `Bedrock__Chat__Engine.send_turn_agentic` |
| Chat widgets (bubble, composer, cost meter, inspector) | ✅ **built** (bedrock-namespaced) | `aws/bedrock/tui/screens/widgets/` |
| SG/Edge action seam + state + `can_act()` | ✅ **built** | `SG_Edge__TUI__Data_Source` + Control Center |
| **SG/Edge tool-API provider** | ❌ **new** (mirror S3) | `sg_edge/tui/tui_api/SG_Edge__Tui_Api__Provider` |
| **Cockpit host screen** (chat column + state + actions + debug) | ❌ **new** (compose existing widgets) | `sg_edge/tui/screens/SG_Edge__TUI__Screen__Cockpit` |
| Curated loadout ("operate-local-edge") + `sg edge tui chat` / `cockpit` command | ❌ **new** (small) | `sg_edge/tui/...` + `Cli__SG_Edge__Tui` |

> The chat widgets are currently under `aws/bedrock/tui/` (the reusable-component-kit
> doc proposes lifting them to the shared `cli/tui/`). v1 imports them where they live
> and flags the lift as a coordinated shared-lib follow-up — do **not** fork them.

---

## 2. Architecture — one edge, two front-ends over it

```
                 Local__Edge__Stack  /  SG_Edge__TUI__Data_Source        ← backend (all logic; tested)
                        ▲                         ▲
        SG_Edge__Tui_Api__Provider.dispatch()     │ (read state + can_act)
                        ▲                         │
            Tui_Api__Execution_Center  ───────────┘   ← scope · precondition · dry-run/confirm · cost · audit
                        ▲                         ▲
        Bedrock__Chat__Engine.send_turn_agentic   │  the action keys (n/g/S/X) call the SAME source
                        ▲                         │
   ┌────────────────────┴─────────────────────────┴─────────────────────────────────┐
   │  SG_Edge__TUI__Screen__Cockpit  (one Textual app)                                │
   │  [Chat column] · [State + Slugs] · [Actions + Preview] · [Debug Panel]           │
   └──────────────────────────────────────────────────────────────────────────────────┘
```

- **The chat is a consumer** of the SG/Edge provider through the execution center: the
  model can call `sg-edge.local.register`, `…request`, `…setup` — but only actions whose
  **preconditions hold** and whose **scope** the curated loadout granted, with dry-run/
  confirm on destructive and **cost summed per turn**.
- **The manual keys are the same calls** (my Control Center already wires them) — so a
  chat tool-call and a keypress are indistinguishable to the backend, and both surface
  in the **Debug Panel** (which is also the chat's tool log → one shared feed).
- **After any turn or keypress, the right columns re-poll** so the state the human sees
  is always the reality the chat just changed.

---

## 3. UI / UX mockups (ASCII)

### 3.1 The full Cockpit (wide terminal)

```
┌ SG/Edge Cockpit · local · edge.sg-labs.local ───────────────────────────── 14:32 ─┐
│┌ Chat ─ Nova ─┐┌ State ──────────────┐┌ Actions ────────┐┌ Debug ───────────────┐│
││ you ▸ set up ││ ✓ deployed ✓ wildcard││ slug [ alice__ ]││ 14:32:07 tool         ││
││ the edge &   ││ fleet: 1  streak 0/3 ││                 ││  sg-edge.local.setup  ││
││ register     ││┌ Slugs ────────────┐││ [n] register    ││  → ok                 ││
││ alice        │││ slug  state  back ││││ [N] reg dormant ││ 14:32:08 tool         ││
││              │││▸alice ● live …8080│││││ [u] unregister  ││  …local.register      ││
││ ai ▸ ⚙ setup │││ bob   ◐ dorm   —  ││││ [g] request     ││  alice → A+TXT ok     ││
││   ✓          ││└───────────────────┘││ [S] setup       ││ 14:32:08 keypress      ││
││  ⚙ register  ││ Checks              ││ [X] teardown    ││  request alice → 200  ││
││   alice ✓    ││  ✓ all healthy      ││                 ││                       ││
││  alice is    ││                     ││ PREVIEW         ││                       ││
││  live on     ││                     ││  g alice → 200  ││                       ││
││  …:8080      ││                     ││  welcome ·…8080 ││                       ││
││ $0.0021·2⚙   ││                     ││                 ││                       ││
│├──────────────┤│                     ││                 ││                       ││
││▸ type here…  ││                     ││                 ││                       ││
│└──────────────┘└─────────────────────┘└─────────────────┘└───────────────────────┘│
│ [c]hat [d]ebug [Tab]focus · [n]reg [g]req [S]setup [X]teardown · [?]help [q]quit    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

The chat column carries its **own cost meter** (`$0.0021 · 2⚙` = per-turn cost + tool
count) and composer. Tool calls render as `⚙ <action> ✓/✗` bubbles inline in the
transcript — the conversation *shows its work*.

### 3.2 Narrow terminal (the SSM/`docker exec` reality) — collapse to two panes

`[d]` hides the Debug Panel; `[c]` can collapse the chat to a thin strip. At ~100 cols
the default is **Chat + State**, actions folded under the footer hints:

```
┌ SG/Edge Cockpit · local ───────────────────────────────────── 14:32 ─┐
│┌ Chat ─ Nova ──────────────────┐┌ State ───────────────────────────┐│
││ you ▸ register bob, no backend ││ ✓ deployed  ✓ wildcard  fleet: 1 ││
││ ai  ▸ ⚙ register bob (dormant) ││┌ Slugs ──────────────────────────┐││
││      ✓ — bob is registered but │││ ▸ alice  ● live    127.0.0.1:8080│││
││      dormant; first request    │││   bob    ◐ dormant  —            │││
││      wakes the Vault Waker.    │││   eve    ● live    127.0.0.1:8080│││
││      $0.0014 · 1⚙              ││└──────────────────────────────────┘││
│├────────────────────────────────┤│ Checks: ✓ healthy                 ││
││▸ ask or instruct…             ││                                    ││
│└────────────────────────────────┘└────────────────────────────────────┘│
│ [c]hat [d]ebug · type to chat · keys: n g S X · [?]help [q]quit         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 A gated / destructive tool-call (confirm flows the same as the keys)

When the model proposes a DESTRUCTIVE action, the execution center surfaces the **same
confirm** the `X` key uses — the model cannot tear down without the human's `y`:

```
│ ai ▸ I can tear the edge down. Confirm?            │   ┌ Confirm ───────────────────┐
│     ⚙ sg-edge.local.teardown  [DRY-RUN]            │   │ teardown will delete the    │
│       preview: deletes local DNS + stack state     │   │ local DNS + stack state.    │
│                                                    │   │   y confirm    n cancel     │
│ (waiting for confirm…)                             │   └─────────────────────────────┘
```

### 3.4 AWS target — chat sees a read-only edge (honesty / capability gate)

On `--target aws`, `can_act()` is `False`; the loadout grants only READ scopes, so the
model's tool list contains `status`/`check`/`slugs` but **not** `register`/`setup` — an
out-of-scope action is *invisible*, not refused:

```
│ you ▸ register a new slug on the AWS edge                                  │
│ ai  ▸ I can read the AWS edge (topology, slugs, drift) but I have no       │
│       write tools here — mutations are pending Slice 5 (live EC2). On the  │
│       local edge I could register it. Want me to switch?                   │
```

---

## 4. Textual specifics (leveraging the package)

- **Layout = nested `Horizontal`/`Vertical` with `fr` widths + a `Grid` fallback.** The
  Cockpit `compose()` yields `Horizontal( chat-col(1fr) · centre(2fr) · actions(1fr) ·
  Debug__Panel )`. The chat column is a `Vertical`: a `VerticalScroll` of `Chat__Bubble`
  widgets + a `Chat__Cost__Meter` + a `Chat__Composer` (its `Input`/`TextArea`).
- **Reuse the built widgets** (`Chat__Bubble`, `Chat__Composer`, `Chat__Cost__Meter`,
  `Chat__Inspector`) — they're already provider-agnostic-ish; import from
  `aws/bedrock/tui/screens/widgets/` for v1, lift to `cli/tui/` later.
- **Collapsible columns via reactive `set_class('-hidden')`** — exactly how
  `Tui__App` toggles the Debug Panel. `c` toggles chat, `d` toggles debug; the centre
  re-flows. This is the responsive-degradation answer for the SSM/`docker exec` widths.
- **Async tool loop on a worker** — `run_worker(self.turn_worker, thread=True)` (the
  pattern the cf-logs sync screen uses) so the model + multi-tool round-trips don't block
  the UI; `call_from_thread` to append bubbles, update the cost meter, and re-poll the
  state column live as each tool returns.
- **Focus model** — composer focused for typing; `Tab`/`Escape` move focus to the slug
  `DataTable` (its built-in cursor) so the single-letter action keys fire there (avoids
  the "Input eats hotkeys" issue we already hit). `Ctrl+Enter` sends the chat turn.
- **One Debug feed** — inject the **same `Debug__Event_Log`** into the execution center
  and the screen, so chat tool-calls *and* manual keypresses log to the one panel (3.1
  shows both). This is the "GUI teaches the CLI under it" principle, doubled.
- **Notifications + the confirm `ModalScreen`** — reuse `SG_Edge__TUI__Confirm`; the
  execution center's CONFIRM mode pushes it for chat-proposed destructive actions.

---

## 5. The SG/Edge tool-API provider (the one genuinely new backend piece)

`sg_edge/tui/tui_api/SG_Edge__Tui_Api__Provider` — mirrors `S3__Tui_Api__Provider`;
`dispatch()` delegates to the existing data source / `Local__Edge__Stack`:

| Action | Tier | Scope | Preconditions | dry-run |
|---|---|---|---|---|
| `status` / `slugs` / `check` | READ_ONLY | `sg-edge.local:read` | — | n/a |
| `request` | READ_ONLY (simulate) | `sg-edge.local:read` | edge deployed | n/a |
| `register` / `register_dormant` | WRITE | `sg-edge.local:write` | edge deployed | ✓ (`--dry-run` already added) |
| `unregister` | CRUD | `sg-edge.local:write` | slug exists | ✓ |
| `setup` | WRITE | `sg-edge.local:write` | — | ✓ |
| `teardown` | DESTRUCTIVE | `sg-edge.local:admin` | edge deployed | ✓ (confirm) |

`input_schema` for each comes from a Type_Safe params class via `Tui_Api__Schema__Builder`
(no hand-written JSON Schema). `state()` returns the snapshot (drives preconditions);
`can_act()` maps to the write scopes being grantable (AWS → read scopes only). Tests
inject a `Local__Edge__Stack` on a temp dir + an in-memory chat source — no mocks, no AWS.

---

## 6. Build slices (bounded; one PR + debrief each)

| Slice | Scope |
|---|---|
| **K1 — provider** | `SG_Edge__Tui_Api__Provider` (read actions first: status/slugs/check/request) + params schemas + SKILL-*.md + register it; contract test-asserts pass. No chat yet — driveable via `sg edge tui api invoke`. |
| **K2 — provider mutations** | register/register_dormant/unregister/setup/teardown with scopes, preconditions, dry-run; pilot through the execution center (gate + confirm) with a real `Local__Edge__Stack`. |
| **K3 — Cockpit shell** | `SG_Edge__TUI__Screen__Cockpit`: the multi-column layout (3.1) reusing the chat widgets + my state/slugs/actions; `c`/`d` toggles; shared `Debug__Event_Log`; **read-only chat first** (no tools) to prove the column + layout. |
| **K4 — wire the agent** | curated "operate-local-edge" loadout → `send_turn_agentic` against the provider; tool bubbles; per-turn cost meter; confirm modal on destructive; re-poll state after each turn. `sg edge tui cockpit` (and/or `chat`). |
| **K5 — docs** | guide section + README row + a per-slice debrief (what worked / what you'd reject — the SSM-width finding especially). |

---

## 7. Acceptance criteria

1. `sg edge tui cockpit` shows the chat column left of the live State/Slugs/Actions; `c`/`d` collapse chat/debug and the layout reflows (works at ~100 cols).
2. Typing "set up the edge and register alice" makes the model call `sg-edge.local.setup` then `register`; the Slugs table shows `alice ● live` without a manual refresh.
3. Every chat tool-call and every manual keypress appears in the one Debug Panel; the chat cost meter sums model + tool cost per turn.
4. A model-proposed `teardown` triggers the same `y/n` confirm the `X` key uses; declining cancels.
5. `--target aws`: the model has only read tools; it explains it can't mutate (pending Slice 5); no keypress or tool-call raises.
6. The chat owns no logic — every tool = one `SG_Edge__TUI__Data_Source` call = one `sg edge local *` verb (separation guide); pilot tests pass with a real stack, no mocks; pure layers run on 3.11.

---

## 8. Risks / open questions

- **Column width over SSM.** Four columns is a lot at 80–100 cols; mitigation is the
  collapse bindings (3.2) + sensible `fr` defaults. If it's still cramped, fall back to
  *chat-or-controls* (one visible at a time, `Tab` swaps) — capture the finding either way.
- **Chat widgets are bedrock-namespaced.** v1 imports them in place; the clean lift to
  `cli/tui/` is a coordinated shared-lib change with the chat agent (don't fork).
- **Default loadout scope.** v1 = local-only, write scopes granted; AWS read-only. Open
  question for the owner: should the chat's *default* loadout include the destructive
  `teardown` scope (gated + confirm), or require an explicit `--allow-destructive`?
- **Model availability / cost.** The chat needs Bedrock creds + a budget ceiling; the
  no-creds path is the scripted in-memory source (tests + a demo loadout).

---

## 9. Explicitly out of scope (seamed, not built)

- Lifting the chat widgets into `cli/tui/` — separate, coordinated.
- AWS-target mutations — stay read-only until v0.2.37 Slice 5 flips `can_act()`.
- The VFS skills tree / multi-turn workflow curation beyond one "operate-local-edge"
  loadout — the tool-API standard covers it; this plan consumes the minimum.
- A standalone "everything" cockpit across all SG/Edge screens — the Cockpit is the
  Control Center + chat; the tabbed dashboard remains the all-screens view.
