---
title: "Bedrock Chat TUI — the reusable component kit (mirroring the JS model)"
file: 03__reusable-component-kit.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: BRIEF — exploration. The reuse contract for chat TUIs.
parent: README.md
---

# Bedrock Chat TUI — reusable component kit

The user's explicit ask: **"for each `sg aws` area where we add a TUI, create components
that can be easily reused in other TUIs"** — mirroring the project's JS UI, where "just
about everything is a reusable component that can then be mixed into tools." This doc
defines the chat component kit, maps it to the JS model, and shows how `sg edge tui`
embeds it as a "chat mode."

---

## 1. The honest starting point: today there is *no* shared TUI kit

Confirmed by reading all three existing TUIs. Each re-implements the same primitives
locally — there is **no** shared component library:

| Component | `sg_edge/tui` | `s3/tui` | `cf/tui` |
|---|---|---|---|
| App base (q/?/t/e bindings) | `SG_Edge__TUI__App__Base` | re-implemented inline | each its own |
| Status glyphs | `SG_Edge__TUI__Glyphs` | — | `CF_TUI__Glyphs` (copy) |
| Help modal | `SG_Edge__TUI__Help` | — | — |
| Export card | `SG_Edge__TUI__Card` | — | `CF_TUI__Card` (copy) |
| Sparkline / Metrics | `SG_Edge__TUI__Metrics` | — | — |

`sg_edge/tui` is the richest and effectively the *de facto* pattern, but its components
are namespaced to `SG_Edge__` and not yet extractable. **This is the gap the brief
names.** The right response is *not* to stop and refactor all three now (that violates
the exploration stance — playbook §1), but to build the **new** chat components in a
reusable shape and place, and let the existing duplication be resolved at the "promotion
conversation" (playbook §9).

---

## 2. Two tiers: generic chat kit vs. Bedrock glue

The cleanest reuse boundary — and the one that directly matches the JS model — splits
**provider-agnostic chat UI** from **Bedrock-specific service glue**:

```
sgraph_ai_service_playwright__cli/aws/_shared/tui/chat/      ← TIER 1: generic, reusable
  widgets/
    Chat__Transcript      VerticalScroll host; mount_user()/mount_assistant(); anchor-to-bottom
    Chat__Bubble          Markdown subclass; role-styled (scoped DEFAULT_CSS); streams via get_stream
    Chat__Composer        TextArea subclass; Enter=send (⇧Enter=newline); emits Submitted message
    Chat__Cost__Meter      reactive sidebar widget; data_bind to a cost-summary object
  schemas/
    Schema__Chat__Cost__Summary   provider-agnostic: turns, in/out tokens, $, budget  (Type_Safe)
  contracts/
    Chat__Engine__Contract        what any chat backend must provide: send_turn(session, text, on_delta)
    Chat__Context__Provider       context() → (label, body)  — the "talk to the data" seam

sgraph_ai_service_playwright__cli/aws/bedrock/tui/           ← TIER 2: Bedrock glue
  service/Bedrock__Chat__Engine        implements Chat__Engine__Contract over the Bedrock primitives
  source/Bedrock__Chat__AWS_Source     wraps Runtime client + Stream adapter
  screens/Bedrock__Chat__Model__Picker Nova picker (priced from Bedrock__Cost__Calculator)
  screens/Bedrock__Chat__Screen        composes the Tier-1 widgets + the Bedrock engine
```

**Tier 1 is the reusable component library.** It imports Textual but **no Bedrock, no
boto3, no AWS** — it knows nothing about Nova. It takes a `Chat__Engine__Contract` and a
`Schema__Chat__Cost__Summary` and renders them. Any future TUI (sg edge, cf, a generic
`sg chat`) can compose these widgets against its own engine.

**Tier 2 is the glue** that satisfies the contract using the Bedrock primitives.

> **The kit is bigger than chat widgets now.** The ratified TUI API standard makes *every*
> chat TUI both a **consumer** of tools and a **provider** of its own surface. The reusable
> machinery for that — `Tui_Api__Provider`, the registry, the execution center, the loadout —
> lives one level up at `cli/tui/tool_api/` (standard §9), not in `_shared/tui/chat/`. A chat
> TUI **composes both**: the Tier-1 chat widgets here + the `tool_api` provider/consumer
> there. The reuse story is therefore "mix chat widgets **and** a TUI API surface into any
> tool," not just widgets.

> **Exploration caveat.** For the very first slices it is acceptable to build the chat
> widgets *inside* `bedrock/tui/screens/widgets/` and **promote them to `_shared/tui/chat/`
> once the shapes settle** (the sixth conversation). Designing them against the contract
> from day one is what makes that promotion a move, not a rewrite. The plan (`04`) flags
> the promotion as an explicit step, not MVP.

---

## 3. Mirroring the JS reusable-component model

The JS UI (`sgraph_ai_service_playwright__api_site/components/`) is **Web
Components**: encapsulated custom elements with shadow-DOM-scoped CSS, props in,
events out, composed declaratively into pages, no shared global state. Textual maps onto
this almost one-to-one:

| JS Web Component idiom | Textual equivalent | In our kit |
|---|---|---|
| `class X extends HTMLElement` / `SgComponent` | `class X(Widget)` / subclass the widget you extend | `Chat__Bubble(Markdown)`, `Chat__Composer(TextArea)` |
| Shadow-DOM scoped CSS | `DEFAULT_CSS` (scoped by default) | each widget owns its CSS; role styling via classes |
| `observedAttributes` / props | `reactive()` attributes + `data_bind()` | `Chat__Cost__Meter` binds to the cost summary |
| `connectedCallback()` | `on_mount()` | transcript anchors, composer focuses |
| `attributeChangedCallback` | `watch_<name>()` | meter re-renders on cost change |
| `dispatchEvent(new CustomEvent(...))` (events bubble up) | custom `Message` classes (bubble up the DOM) | `Chat__Composer.Submitted`, `Chat__Bubble.Edited` |
| no prop-drilling; parent listens for events | screen handles bubbled messages; no logic in children | screen owns the engine; widgets stay dumb |
| composition in an HTML template | `compose()` / nested containers | `Bedrock__Chat__Screen.compose()` |
| one component per file | one class per file (CLAUDE.md rule 21) | already the house style |

The principle that makes a JS component reusable here is the same one CLAUDE.md already
enforces for the data layer: **encapsulation + no shared global state + props down /
events up.** A `Chat__Bubble` knows only its own text and role; it never reaches into the
session. The screen wires children to the engine. That is exactly "mix components into
tools."

**Reusable widget skeleton** (the JS `customElements.define` analogue):

```python
class Chat__Bubble(Markdown):                       # extends the widget it specialises
    DEFAULT_CSS = """                               # scoped — the shadow-DOM analogue
    Chat__Bubble { margin: 1 2; padding: 0 1; border: round $surface; }
    Chat__Bubble.-user      { border: round $primary; }
    Chat__Bubble.-assistant { border: round $success; }
    """
    role = reactive("assistant")                    # prop

    class Edited(Message):                           # event out (bubbles up)
        def __init__(self, bubble, text): self.bubble = bubble; self.text = text; super().__init__()

    def watch_role(self, _old, new):                 # attributeChangedCallback analogue
        self.set_classes(f"-{new}")
```

---

## 4. The kit's first citizens (what this brief actually delivers)

| Component | Tier | Reused by (intended) | Reusable because |
|---|---|---|---|
| `Chat__Transcript` | 1 | any chat TUI | knows nothing but "mount a bubble, stay at bottom" |
| `Chat__Bubble` | 1 | any chat TUI | role + markdown; streams via `get_stream`; scoped CSS |
| `Chat__Composer` | 1 | any input TUI (not just chat) | a submit-on-Enter `TextArea` is generally useful |
| `Chat__Cost__Meter` | 1 | any LLM TUI | binds to a provider-agnostic cost summary |
| `Chat__Inspector` | 1 | any LLM TUI | shows exact request/response per turn (built; the honesty + multi-turn-proof surface) |
| `Chat__Engine__Contract` | 1 | every chat backend | the seam that lets the same UI front any LLM |
| `Chat__Context__Provider` | 1 | `sg edge tui`, cf tui, … | "talk to *this* screen's data"; **for large data, hands a VFS tree, not an inlined body** (see §5) |
| `Bedrock__Chat__Engine` | 2 | Bedrock chat TUI | the Nova-specific implementation |
| `Bedrock__Chat__Model__Picker` | 2 | Bedrock chat TUI | Nova-priced; trivially extended to other providers later |

---

## 5. How `sg edge tui` gets a chat mode (the user's actual end-goal)

The user is working on `sg edge tui` and wants to "talk with that data, capture ideas,
and create dev briefs." Because the chat kit is Tier-1 generic and takes a
`Chat__Context__Provider`, the edge TUI embeds it with **no changes to the chat code**:

1. `sg edge tui` already builds a normalised `Schema__SG_Edge__TUI__Snapshot` and has a
   `Card` renderer. Implement `Chat__Context__Provider.context()` to return
   `("edge snapshot @ {time}", card.render(snapshot))`.
2. Add a `c` binding to the edge App that does
   `push_screen(Bedrock__Chat__Screen(context_provider=self))`.
3. The operator, looking at a dormant slug, hits `c` and asks "why is alice dormant?" —
   the model answers against the **real snapshot**, and `b` writes a dev brief to the
   agent-output folder.

> **Small snapshot vs. large reference set.** Returning `card.render(snapshot)` as an inlined
> body is right for a *small, always-relevant* snapshot. When a host wants to expose a *large*
> body (many screens, a doc set, history), `Chat__Context__Provider` should instead **mount a
> VFS tree** (`populate_vfs`, TUI API standard §6) and let the model pull on demand — not
> inline 50k tokens up front. The seam is the same; only small/now context is inlined.

This is the concrete reuse win: **one chat kit, embedded in every rich read-only TUI,
turning each into a place you can diagnose and emit action plans** — the AWS-Q-style
experience, built reusable-first. And because each such TUI is also a TUI API **provider**,
the embedding composes both ways: the host drives the chat, and the chat reads the host's
data — a concrete **TUI-of-TUIs**.

```
   sg edge tui (read-only screens)            sg aws bedrock chat tui (standalone)
            │  c (chat mode)                              │
            ▼                                             ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  _shared/tui/chat  (Tier 1: Transcript, Bubble, Composer,      │   ← reusable
   │                     CostMeter, Engine contract, Context seam)  │
   └──────────────────────────────────────────────────────────────┘
            │  satisfied by
            ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  bedrock/tui  (Tier 2: Bedrock__Chat__Engine over Nova)        │   ← glue
   └──────────────────────────────────────────────────────────────┘
```

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
