---
title: "Bedrock Chat TUI — architecture"
file: 01__architecture.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: BRIEF — exploration, not production.
parent: README.md
---

# Bedrock Chat TUI — architecture

Covers per-service-template §1–3 (data that exists, the primitives, the data-source
seam) plus the engineering shape: module layout, new Type_Safe schemas, the two
additive primitive extensions, the in-memory session/cost model, and the
streaming-worker pattern.

---

## 1. What real data exists today  ‹be ruthlessly honest›

This TUI is unusual for the project: its "data" is not a passive resource to read — it
is a **live LLM call**. Everything the screen shows is produced by a real Bedrock
`converse` against a real Nova model. There is no synthetic mode (a fake response would
be dishonest tooling — playbook §7); tests use an **in-memory source that returns canned
deltas**, clearly a test double, never shown to an operator.

| Data / resource | EXISTS / PROPOSED | Where it lives | Volume / cadence |
|---|---|---|---|
| Nova model inventory (`micro/lite/pro/premier`) | **EXISTS** | `Bedrock__Model__Aliases.py` → `BEDROCK_MODEL_ALIASES['nova']` | static, 4 models |
| Per-1M-token Nova pricing | **EXISTS** | `Bedrock__Cost__Calculator._PRICING` | static, 4 rows |
| Per-turn tokens (`inputTokens`/`outputTokens`) | **EXISTS** (non-stream) / **GAP** (stream) | Bedrock `converse` `usage` block | per call |
| Per-turn USD cost estimate | **EXISTS** | `Bedrock__Cost__Calculator.estimate()` | per call |
| Multi-turn conversation history | **PROPOSED** | none — `converse` is hardcoded single-turn | n/a |
| Session cost/token aggregate | **PROPOSED** | none — no session object exists | n/a (in-memory, ephemeral) |
| Streaming token counts | **GAP** | the `metadata` event exists in the Bedrock stream but the adapter ignores it | per call |
| Durable transcript / brief | **EXISTS** (mechanism) | `Bedrock__Capture__Writer` (`~/.sg/aws/bedrock/chat/...`) | opt-in per export |

**Honest summary:** the *primitives* exist and are solid; what's PROPOSED is the
**conversation** (multi-turn) and the **session aggregate** — both of which are pure
in-memory state the TUI owns for its lifetime and is content to lose on close.

---

## 2. The primitives that back it

| Primitive | Reads / does | Pure? | File |
|---|---|---|---|
| `Bedrock__Runtime__AWS__Client.converse` | single-turn Converse call → raw resp | boto3 boundary | `bedrock/service/Bedrock__Runtime__AWS__Client.py:31` |
| `…converse_stream` | single-turn streaming generator | boto3 boundary | `…:39` |
| `…extract_text` / `…extract_usage` | pull text + `(in,out)` tokens from a resp | pure | `…:50` / `…:57` |
| `Bedrock__Model__Resolver.resolve` | `(provider, alias, region)` → model ID | pure | `bedrock/service/Bedrock__Model__Resolver.py` |
| `Bedrock__Cost__Calculator.estimate` | `(model_id, in, out)` → USD | **pure, Type_Safe** | `bedrock/service/Bedrock__Cost__Calculator.py:54` |
| `…check_cost_cap` | refuse if predicted cost > cap | pure | `…:73` |
| `Bedrock__Stream__Adapter.extract_delta` / `collect` | delta text from a stream event | pure | `bedrock/service/Bedrock__Stream__Adapter.py:21` / `:28` |
| `Bedrock__Capture__Writer.write_chat` | persist a record under `~/.sg/aws/bedrock/chat/` | sink boundary | `bedrock/service/Bedrock__Capture__Writer.py` |

**Do not reuse `run_chat()`** (`Verb__Bedrock__Chat__Helpers.py:106`). It is the CLI
orchestrator and is welded to the terminal: it calls `typer.echo`, builds `rich.Panel`s,
raises `typer.Exit`, and is **single-turn**. The TUI needs the same *steps* with none of
the printing. We factor those steps into a pure `Bedrock__Chat__Engine` (§4) that
returns data and never touches stdout — the engine and `run_chat()` then sit
side-by-side over the same lower primitives.

---

## 3. The two primitive extensions (small, additive, non-breaking)

Per playbook §2.1, when the TUI needs data the primitives don't expose, **extend the
primitive** rather than grow parallel state in the view. Two minimal extensions:

### 3.1 Multi-turn Converse

`converse(model_id, prompt, region)` hardcodes `messages=[{'role':'user','content':[{'text':prompt}]}]`.
Add a sibling that accepts a full message list (and an optional system prompt). The
existing single-turn method stays exactly as-is for the CLI.

```python
# Bedrock__Runtime__AWS__Client  (added methods — boto3 boundary unchanged)

def converse_messages(self, model_id: str, messages: list,
                      region: str = None, system: str = None) -> dict:
    runtime = self.client(region or self.current_region())
    kwargs  = dict(modelId=model_id, messages=messages)
    if system:
        kwargs['system'] = [{'text': system}]            # Bedrock system block
    return runtime.converse(**kwargs)

def converse_stream_messages(self, model_id: str, messages: list,
                             region: str = None, system: str = None):
    runtime = self.client(region or self.current_region())
    kwargs  = dict(modelId=model_id, messages=messages)
    if system:
        kwargs['system'] = [{'text': system}]
    stream = runtime.converse_stream(**kwargs).get('stream')
    if stream:
        for event in stream:
            yield event
```

`messages` is the canonical Bedrock shape — the session builds it from its message log:
`[{'role':'user','content':[{'text':...}]}, {'role':'assistant','content':[{'text':...}]}, ...]`.
This is what makes the chat a *conversation* rather than a sequence of unrelated calls.

### 3.2 Streaming that keeps the token count (the cost-critical fix)

Today, streaming sets `input_tokens = output_tokens = 0` (`Verb__Bedrock__Chat__Helpers.py:135`)
because the adapter only extracts `contentBlockDelta`. But Bedrock's `converse_stream`
emits a terminal **`metadata`** event carrying `usage` (`inputTokens`, `outputTokens`,
`totalTokens`) and `metrics.latencyMs`. Extracting it gives us **streaming UX *and*
accurate cost** — non-negotiable given the brief's emphasis on cost.

```python
# Bedrock__Stream__Adapter  (added — pure)

def extract_usage(self, event: dict):                    # → (in, out, latency_ms) | None
    meta = event.get('metadata')
    if meta:
        usage   = meta.get('usage', {})
        metrics = meta.get('metrics', {})
        return (int(usage.get('inputTokens', 0)),
                int(usage.get('outputTokens', 0)),
                int(metrics.get('latencyMs', 0)))
    return None

def collect_with_usage(self, stream_events):             # → (text, in, out, latency_ms)
    parts = []; usage = (0, 0, 0)
    for event in stream_events:
        delta = self.extract_delta(event)
        if delta:
            parts.append(delta)
        u = self.extract_usage(event)
        if u is not None:
            usage = u
    return (''.join(parts), *usage)
```

For the *live* TUI the source yields each delta as it arrives (so the bubble streams)
and emits the usage tuple when the `metadata` event lands — the engine prices the turn
the instant the stream completes.

> Both extensions ship in the **pure data layer** with full unit tests (no Textual, runs
> on 3.11) — slice **T1** in the plan. They are independently useful: the CLI's
> `--stream` path can adopt `collect_with_usage` to stop reporting `tokens=0`.

---

## 4. The session / cost model (the heart of the brief)

Three new Type_Safe schemas + one pure engine + one swappable source. **Schemas are
pure data, no methods** (CLAUDE.md rule 4/5); all mutation lives in the engine.

### 4.1 Schemas (`bedrock/tui/schemas/`, one class per file)

```python
# Enum__Bedrock__Chat__Role
class Enum__Bedrock__Chat__Role(Enum):
    USER      = 'user'
    ASSISTANT = 'assistant'
    SYSTEM    = 'system'

# Schema__Bedrock__Chat__Message            — one line of the conversation
class Schema__Bedrock__Chat__Message(Type_Safe):
    role : Enum__Bedrock__Chat__Role
    text : str
    ts   : float                              # epoch seconds (capture moment)

# Schema__Bedrock__Chat__Turn               — the cost/telemetry record for one exchange
class Schema__Bedrock__Chat__Turn(Type_Safe):
    model_id      : Safe_Str__Bedrock__Model_Id
    input_tokens  : int
    output_tokens : int
    cost_usd      : float                     # from Bedrock__Cost__Calculator.estimate()
    latency_ms    : int                       # from the metadata event
    ts            : float

# Schema__Bedrock__Chat__Session            — in-memory, ephemeral; lost on close (by design)
class Schema__Bedrock__Chat__Session(Type_Safe):
    session_id          : Safe_Str__Bedrock__Session_Id
    provider            : str                 # 'nova' for now
    model_alias         : str                 # 'lite' (default) | 'micro' | 'pro' | 'premier'
    region              : str
    started_at          : float
    messages            : List__Bedrock__Chat__Message
    turns               : List__Bedrock__Chat__Turn
    total_input_tokens  : int                 # running aggregate (engine maintains)
    total_output_tokens : int
    total_cost_usd      : float
    turn_count          : int
    budget_usd          : float               # soft session budget for the meter (default 0.50)
```

`Safe_Str__Bedrock__Session_Id` and `…Model_Id` already exist in
`bedrock/primitives/`. The cost aggregates are plain running sums the engine updates per
turn — cheap and exact, never re-derived from a backend.

### 4.2 The engine (`bedrock/tui/service/Bedrock__Chat__Engine.py`, pure orchestration)

This is the thin, printing-free replacement for `run_chat()`. It is the **only** place
that knows how a turn is executed; the view layer just calls `send_turn` and renders.

```python
class Bedrock__Chat__Engine(Type_Safe):
    source   : Bedrock__Chat__Source                 # injected (AWS | in-memory)
    resolver : Bedrock__Model__Resolver = None
    calc     : Bedrock__Cost__Calculator = None      # reuse the existing pure calculator

    def send_turn(self, session, user_text, on_delta=None):
        # 1. append the user message, resolve the Nova model
        # 2. build the Bedrock messages list from session.messages
        # 3. pre-flight: calc.check_cost_cap(model_id, len(history_chars))  → raise if over
        # 4. stream via source.stream_turn(...); call on_delta(chunk) per delta
        # 5. on the metadata event: (in, out, latency) → calc.estimate(...) → cost
        # 6. append the assistant message + a Schema__Bedrock__Chat__Turn
        # 7. update the running aggregates; return the Turn
        ...
```

`on_delta` is the seam the Textual worker uses to push tokens into the bubble (§5). The
engine has **zero** Textual/Rich imports — it is unit-tested on 3.11 against the
in-memory source with hand-built deltas, asserting on the returned `Turn` and the
mutated `session` aggregates. No mocks.

### 4.3 The source seam (`bedrock/tui/source/`)

Mirrors the `sg edge tui` data-source pattern (swap live AWS for an in-memory fake in
tests — the no-mocks discipline).

```python
class Bedrock__Chat__Source(Type_Safe):              # interface
    def stream_turn(self, model_id, messages, region, system=None):
        raise NotImplementedError                    # yields ('delta', text) | ('usage', (in,out,ms))

class Bedrock__Chat__AWS_Source(Bedrock__Chat__Source):
    runtime : Bedrock__Runtime__AWS__Client          # the existing boto3 boundary
    adapter : Bedrock__Stream__Adapter
    # wraps converse_stream_messages + extract_delta/extract_usage

class Bedrock__Chat__In_Memory(Bedrock__Chat__Source):
    scripted : List__... = None                      # canned deltas + usage for tests
```

### 4.4 Cost discipline (why this satisfies "cost is VERY important")

- **Per-turn**: every assistant bubble footer shows `in=… out=… $0.000123 · 412ms`,
  computed from the real `metadata` usage, not an estimate.
- **Per-session**: the docked sidebar shows running `Σ tokens` and `Σ $`, plus a
  **budget bar** (`$0.012 / $0.50`). Reuses `Bedrock__Cost__Calculator` verbatim.
- **Pre-flight cap**: the engine calls the existing `check_cost_cap` *before* each send,
  accounting for the **growing history** (multi-turn prompts get more expensive). Over
  the cap → a blocking confirm modal (`push_screen_wait`), never a silent overspend.
- **Ephemeral by design**: the session lives only in memory. Losing it on close is the
  accepted behaviour; durable capture is the opt-in `export` / `brief` action.

---

## 5. The streaming-worker pattern (Textual 8.x, the cost-accurate version)

boto3's `converse_stream` is a **blocking** generator, so the live stream runs on a
**thread worker** and marshals back to the UI thread. `exclusive=True, group="llm"` so a
new prompt cancels an in-flight stream.

```python
from textual import work

@work(thread=True, exclusive=True, group="llm")
def stream_reply(self, user_text: str) -> None:
    bubble = self.mount_assistant_bubble()                 # a Markdown subclass (Chat__Bubble)
    def on_delta(chunk: str):
        self.call_from_thread(bubble.append_md, chunk)     # MarkdownStream coalesces writes
    turn = self.engine.send_turn(self.session, user_text, on_delta=on_delta)
    self.call_from_thread(self.cost_meter.refresh_from, self.session)   # update sidebar
    self.call_from_thread(self.notify_if_over_budget)
```

- The **transcript** is a `VerticalScroll(id="transcript")`; on each new turn we mount a
  user `Chat__Bubble` then an assistant one, and call `container.anchor()` so the view
  sticks to the bottom as tokens stream (releases when the user scrolls up).
- The assistant bubble wraps Textual's **`Markdown.get_stream()` → `MarkdownStream`**
  (v5.0.0+), which **coalesces** bursts of tokens into one render and re-parses only the
  last markdown block — this is what kills flicker *and* keeps it readable over the
  SSH/SSM chain at 5–10 Hz (playbook §4). We feed tokens as fast as they arrive and let
  the stream throttle to the link.
- The **composer** is a `TextArea` subclass that intercepts Enter to submit
  (Shift+Enter = newline) and emits a custom `Submitted` message the screen handles.
- On completion the worker prices the turn (already done inside `send_turn`) and refreshes
  the cost sidebar via `data_bind`/reactive.

---

## 6. Module layout (mirrors `sg_edge/tui`)

```
sgraph_ai_service_playwright__cli/aws/bedrock/tui/
  bedrock_chat_tui__config.py     model default (lite), region, budget default, refresh, card width
  enums/
    Enum__Bedrock__Chat__Role            (USER / ASSISTANT / SYSTEM)
  schemas/
    Schema__Bedrock__Chat__Message
    Schema__Bedrock__Chat__Turn
    Schema__Bedrock__Chat__Session
    Schema__Bedrock__Chat__Context       (label + body — the "talk to the data" seam, §arch 7)
    List__Bedrock__Chat__{Message,Turn}
  source/
    Bedrock__Chat__Source                interface
    Bedrock__Chat__AWS_Source            wraps Runtime client + Stream adapter
    Bedrock__Chat__In_Memory             scripted deltas/usage for tests (no mocks)
  service/
    Bedrock__Chat__Engine                pure: send_turn → mutate session, return Turn
    Bedrock__Chat__Card                  pure: session → ASCII transcript+cost card (export/OSC-52)
    Bedrock__Chat__Brief__Builder        pure: session (+context) → dev-brief markdown
  screens/
    Bedrock__Chat__Screen                the App: transcript + composer + cost sidebar
    Bedrock__Chat__Render                pure: session → markup helpers (footers, bubble text)
    Bedrock__Chat__Model__Picker         ModalScreen[str]  — Nova picker with live pricing
    Bedrock__Chat__Brief__Modal          ModalScreen — confirm/preview a brief before writing
    widgets/                             (chat widgets — promote to _shared/tui/chat/, see kit doc)
      Chat__Transcript  Chat__Bubble  Chat__Composer  Chat__Cost__Meter
  cli/
    Cli__Bedrock__Chat__Tui              `sg aws bedrock chat tui` + `diagnose`
  tests/                                 co-located, pilot + in-memory source, gated on textual
```

One external touch: a single `add_typer`/`@app.command` line so
`sg aws bedrock chat tui` appears under the existing `chat` group
(`bedrock/cli/chat/Cli__Bedrock__Chat.py`). Nothing else imports `tui`. Textual is
imported **lazily inside the command body** so the rest of the CLI never requires it
(matches `sg edge tui`).

### Convention boundary (CLAUDE.md rule 1 carve-out)
Same split the `sg edge tui` plan ratified: the **data/schema/enum/source/engine/card/
brief layer** is `Type_Safe`, zero raw primitives, `Enum__*` for fixed sets, one class
per file, 80-char headers, no docstrings — **all logic + cost + tests live here**. The
**view layer** (App / Screen / widgets) subclasses Textual's `App`/`Widget`/`Markdown`/
`TextArea` (framework carve-out) and holds **no business logic** — it renders the session
and routes keys/deltas to the engine.

---

## 7. The "talk to the data" seam — context injection

The user's deeper goal (the AWS-Q analogy): not a blank chatbot, but a way to *talk
about the current TUI's data*, diagnose gaps, and emit a dev brief. Designed in via
`Schema__Bedrock__Chat__Context` (`label` + `body`):

- **MVP / standalone**: `sg aws bedrock chat tui --context FILE` seeds the session with a
  file's content as a system block (e.g. a pasted edge snapshot, a reality-doc page).
- **Phase 2 / embedded**: `sg edge tui` gains a `c` ("chat") binding that opens the chat
  screen pre-seeded with **its live snapshot rendered to markdown** as the context body.
  Because `sg edge tui` already produces a normalised `Schema__SG_Edge__TUI__Snapshot`
  and a `Card` renderer, the context body is just `card.render(snapshot)` — no new data
  plumbing. The operator then asks "why is slug X dormant?" against real state.
- **Brief capture**: `Bedrock__Chat__Brief__Builder` turns the session (+ the context it
  was seeded with) into a dev-brief markdown and writes it via the existing
  `Bedrock__Capture__Writer` pattern to `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/`
  — the bridge from "talked about a gap" to "coding agent has a brief."

The context body is **labelled in the UI** (`context: edge snapshot @ 10:31`) so it's
never ambiguous what the model was told (honesty rule).

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
