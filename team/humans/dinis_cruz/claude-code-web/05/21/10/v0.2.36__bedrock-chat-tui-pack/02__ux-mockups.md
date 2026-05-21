---
title: "Bedrock Chat TUI — UX mockups & the best 2026 text-chat experience"
file: 02__ux-mockups.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: BRIEF — exploration. Sketches are starting points, not specifications.
parent: README.md
---

# Bedrock Chat TUI — UX mockups

> These are **starting points, not specifications** (playbook §1). The implementing
> agent should deviate and write down what worked and what didn't. Sketches use the
> project's box/block idioms (playbook §5.4).

---

## 0. What "best text-chat UX, May 2026" means — and how Textual delivers it

The bar for a terminal chat in 2026 is set by tools like Claude Code, `aichat`, and
Amazon Q's CLI. The features that make those feel good — and the **specific Textual 8.x
mechanism** that gives us each — are:

| UX expectation | Textual mechanism (confirmed) | Notes |
|---|---|---|
| Tokens stream in smoothly, no flicker | **`Markdown.get_stream()` → `MarkdownStream`** (v5.0.0) | coalesces token bursts into one render; re-parses only the last block |
| Rich rendering of replies (code, tables, lists) | `Markdown` widget per bubble | code blocks get syntax highlight + indent guides; tables render |
| Multi-line composer, Enter to send | `TextArea` subclass intercepting Enter (Shift+Enter = newline) | TextArea has **no** native submit — we add it |
| Transcript auto-sticks to the bottom | `VerticalScroll.anchor()` (v4 semantics) | releases when the user scrolls up to read history |
| "Assistant is typing…" affordance | `widget.loading = True` / `LoadingIndicator` | shown on the pending bubble until first token |
| Cancel a runaway/expensive reply | `@work(exclusive=True, group="llm")` + Esc | a new prompt or Esc cancels the in-flight stream |
| Switch model without leaving chat | `ModalScreen[str]` + `push_screen_wait` | Nova picker with live pricing |
| Fuzzy commands (new / clear / export / model) | built-in **Command Palette** (Ctrl+P) | register `SystemCommand`s |
| Non-blocking status ("copied", "over budget") | `self.notify(...)` toasts | bottom-right, severity-coloured |
| Theme switch, light/dark | reactive `App.theme` + `t` key | reuse the `sg edge tui` toggle |
| Copyable replies | `Markdown` text selection (v4+) | plus OSC-52 card export for the whole session |

The single most important one is **`MarkdownStream`**: it is purpose-built for LLM token
streams and is also the lever that keeps the experience smooth over the SSH/SSM chain
(playbook §4) — it throttles to whatever the link can carry instead of emitting a frame
per token.

---

## 1. The main chat screen — `sg aws bedrock chat tui`

Three regions: a growing **transcript** (left, `1fr`), a docked **cost/session sidebar**
(right, `width: 34`), and a docked **composer** (bottom, `height: auto`).

```
┌─ sg aws bedrock chat ─ nova-lite ─ eu-west-2 ─────────────────────────┬─ session ──────────────┐
│                                                                        │ model  nova-lite        │
│  ╭─ you · 10:31:02 ─────────────────────────────────────────────╮     │ region eu-west-2        │
│  │ why might edge slug "alice" be dormant but its backend up?    │     │ turns  3                │
│  ╰──────────────────────────────────────────────────────────────╯     │                         │
│                                                                        │ tokens  in 1,204        │
│  ╭─ nova-lite · 10:31:03 ───────────────────────────────────────╮     │         out 1,840       │
│  │ A dormant slug with a healthy backend usually means the DNS   │     │         Σ   3,044       │
│  │ A/TXT record pair is present but the **wildcard** isn't       │     │                         │
│  │ resolving the slug to the fleet. Check three things:          │     │ cost                    │
│  │                                                               │     │  this turn  $0.000291   │
│  │ 1. `sg edge dns show alice` — is the TXT state `live`?        │     │  session Σ  $0.000713   │
│  │ 2. the fleet IPs vs the A record …                            │     │                         │
│  │ ▌                                                             │     │ budget  $0.50           │
│  │                                                               │     │  ▓▓░░░░░░░░░░░░░ 0.1%    │
│  ╰──────────────────────────────────────────────────────────────╯     │                         │
│                                              ⟳ streaming · 412ms        │ context                 │
│                                                                        │  edge snapshot @ 10:30  │
│                                                                        │  [SEEDED]               │
├────────────────────────────────────────────────────────────────────────┴────────────────────────┤
│ ▌ ask about the edge snapshot…                                                            (nova-lite) │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Enter] send  [⇧Enter] newline  [Esc] stop  [m] model  [b] brief  [e] export  [^L] clear  [?] help │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Per-bubble footer** (assistant): `⟳ streaming · 412ms` while live; on completion it
  becomes `in 412 · out 690 · $0.000291 · 412ms` — the exact, metadata-derived cost,
  per turn. This is the "capture the cost of each chat" requirement made visible.
- **Sidebar** is the session aggregate: running token sums, per-turn + session USD, and
  a **budget bar** that turns amber at 70% and red at 90% (cost-color tokens, §4).
- **Context pane**: when seeded (standalone `--context`, or embedded from `sg edge tui`),
  shows the label + a `[SEEDED]` marker so it's never ambiguous what the model was told.

**Teaches:** is a per-bubble cost footer legible or noisy; is the budget bar the right
pressure; does streaming markdown stay readable over SSM; is the sidebar worth the width
or should cost be a one-line status instead.

---

## 2. Cost detail — folded into the sidebar, expandable

Rather than a separate screen (exploration: keep it bounded), pressing `$` expands a
**per-turn cost table** in a `Collapsible` over the transcript — the Reality-Dashboard
idiom (catalogue §5) applied to spend.

```
┌─ session cost · 3 turns ─────────────────────────────────────────────────┐
│  #  model      in     out     $          ms    ▁▂▃ cost trend             │
│  1  nova-lite  402    210     $0.000088  690   ▁                          │
│  2  nova-lite  400    760     $0.000206  540   ▃                          │
│  3  nova-lite  402    870     $0.000291  412   ▅                          │
│  ─────────────────────────────────────────────                           │
│  Σ            1,204  1,840    $0.000713        avg 547ms                   │
│                                                                           │
│  by model:  nova-lite  3 turns  $0.000713  (100%)                         │
│  [Esc] close   [e] export card                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

A `Sparkline` of per-turn cost (reuses the `sg edge tui` sparkline idiom) makes the
spend trend legible at a glance. **Teaches:** does anyone want per-turn detail, or is the
session Σ enough; is the cost-trend sparkline meaningful for chat.

---

## 3. Model picker — `m`  (Nova only, with live pricing)

A `ModalScreen[str]` returning the chosen alias. **Filtered to Nova** (the brief's
"start with only Nova"); price columns come straight from `Bedrock__Cost__Calculator`.

```
┌─ choose a Nova model ───────────────────────────────────────────┐
│   alias     model id                in $/1M   out $/1M   note    │
│ ▸ lite      amazon.nova-lite-v1:0     0.06      0.24    default  │
│   micro     amazon.nova-micro-v1:0    0.035     0.14    cheapest │
│   pro       amazon.nova-pro-v1:0      0.80      3.20             │
│   premier   amazon.nova-premier-v1:0  2.50     12.50    priciest │
│                                                                  │
│   switching model keeps the conversation; cost is per-model      │
│   [↑↓] move   [Enter] select   [Esc] cancel                      │
└──────────────────────────────────────────────────────────────────┘
```

Switching mid-session keeps the message history (the next turn just resolves to a
different model ID); the per-turn records keep each turn's own model, so the "by model"
breakdown in §2 stays honest. **Teaches:** do people switch models mid-chat; is "cheapest
vs priciest" the right framing for picking Nova tiers.

---

## 4. Brief capture — `b`  (the "create a dev brief" verb)

The payoff for "talk to the data → capture ideas → action plan." `b` opens a modal that
previews a dev brief synthesised from the conversation (and the seeded context), then
writes it via the capture writer.

```
┌─ capture dev brief from this conversation ──────────────────────┐
│ title  ▌ edge slug "alice" dormant — wildcard not resolving      │
│ ────────────────────────────────────────────────────────────────│
│ # Dev brief — edge slug alice dormant                            │
│                                                                  │
│ ## Context (seeded)                                              │
│ edge snapshot @ 10:30 — alice: state=DORMANT, backend 10.0.0.4…  │
│                                                                  │
│ ## Diagnosis (from chat)                                         │
│ - wildcard *.edge.sg-labs.app not resolving alice → fleet        │
│ - TXT state live but A record points at stale fleet IP           │
│                                                                  │
│ ## Proposed actions                                              │
│ - [ ] verify `sg edge dns show alice` TXT vs A …                 │
│ - [ ] …                                                          │
│ ────────────────────────────────────────────────────────────────│
│ writes → team/humans/dinis_cruz/claude-code-web/05/21/10/        │
│ [w] write brief   [e] copy to clipboard   [Esc] cancel           │
└──────────────────────────────────────────────────────────────────┘
```

The brief body is itself produced by a (cheap, Nova-lite) summarisation turn over the
session — so its cost is captured like any other turn. **Teaches:** is an LLM-synthesised
brief good enough to hand a coding agent, or does it need a human edit pass first; where
should briefs land.

---

## 5. States the screen must show honestly

| State | Rendering |
|---|---|
| Idle, no turns yet | empty transcript + a one-line hint "ask anything about Nova — costs are tracked below"; composer focused |
| Streaming | pending assistant bubble with `loading` spinner until first token, then `⟳ streaming · {ms}`; `Esc` cancels |
| Turn complete | bubble footer flips to exact `in/out/$/ms`; sidebar Σ updates; transcript anchors to bottom |
| Over per-call cap | **blocking confirm modal** before send: "this turn ≈ $0.0042, cap $0.0010 — proceed?" (reuses `check_cost_cap`) |
| Over session budget | amber→red budget bar + a `notify(... severity=warning)` toast; sends still allowed (soft budget) unless the operator sets a hard cap |
| Bedrock error (access/region/throttle) | the existing actionable hints (from `_render_bedrock_client_error`) rendered into a bubble, not a traceback |
| No TTY / piped | **one-shot**: read prompt from stdin/arg, run a single non-stream turn, print response + cost line, exit (keeps `chat tui` safe to pipe / run in CI) |
| `$TERM=dumb` | degrade to the no-TTY path |

---

## 6. Keybindings (keyboard-primary, playbook §4)

```
Enter      send               m   model picker
⇧Enter     newline            b   capture dev brief
Esc        stop streaming     $   cost detail
^L         clear chat         e   export session card (file + OSC-52)
PgUp/PgDn  scroll transcript  t   toggle theme
?          help (modal)       Ctrl+P  command palette  q  quit
```

`?` opens the same context-aware Help modal pattern `sg edge tui` uses (walk the MRO
`BINDINGS`). Mouse is enhancement only; everything is reachable from the keyboard.

---

## 7. Theming & cost-color tokens

Reuse the built-in `textual-dark`/`textual-light` toggle. Register **app-specific design
tokens** for the cost states so colour stays semantic (playbook §5.2) and theme-aware:

```
$cost-ok      = $success    # under 70% of budget
$cost-warn    = $warning    # 70–90%
$cost-over    = $error      # > 90% / over cap
```

The budget bar, per-turn footers, and the over-budget toast all read these tokens, so a
theme switch keeps the cost semantics intact. Per-bubble role styling
(`-user`/`-assistant`) uses `$primary` / `$success` borders via the bubble's scoped
`DEFAULT_CSS`.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
