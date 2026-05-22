---
title: "Design Brief — sg tui chat: a shared, multi-provider chat module (Bedrock + Ollama + OpenRouter)"
file: 02__shared-tui-chat-multi-provider.md
author: Dev (Claude)
date: 2026-05-22
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (merged dev v0.2.39 line)
status: PLAN — no code, no commits. For human ratification before any build.
parent:
  - team/comms/plans/v0.2.41__cf-logs-tui-chat/01__brief.md
  - team/claude/debriefs/2026-05-21__v0.2.36-bedrock-chat-tui.md
  - team/humans/dinis_cruz/claude-code-web/05/21/14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md
---

# Design Brief — `sg tui chat`: shared, multi-provider chat

> **PROPOSED — does not exist yet.** Generalises the v0.2.36 Bedrock chat (which is
> already provider-agnostic at its core) into a shared module that any TUI embeds and
> that speaks to **Bedrock, Ollama, and OpenRouter** behind one interface.

---

## 1. One line

A single chat surface — `sg tui chat` and an embeddable widget set — that talks to the
local edge, the CF logs, a reality-doc page, or anything else, against **any** LLM
backend (cloud or local), with per-turn cost where it applies and graceful "free" where
it doesn't.

## 2. The core insight (why this is cheap)

The Bedrock chat **engine is already provider-agnostic**: `Bedrock__Chat__Engine`
delegates every model call to an injected `source` whose seam is:

```python
stream_turn(model_id, messages, region='', system=None)        # yields ('delta', text) | ('usage', (in, out, ms))
converse_turn(model_id, messages, region='', system=None, tool_config=None) -> {stop_reason, content[], input_tokens, output_tokens, latency_ms}
```

That seam **is** the provider interface — it just (a) lives under `aws/bedrock/`, (b)
leaks AWS (`region`) and Bedrock wire shapes (`messages` in converse format, Bedrock
`tool_config`), and (c) the cost/model catalogue is Nova-specific
(`Bedrock__Model__Aliases`, `Bedrock__Cost__Calculator`). Generalise those three and the
multi-provider module falls out. **No engine rewrite.**

## 3. Target layout — promote the neutral core to `cli/tui/chat/`

```
cli/tui/chat/
  engine/Chat__Engine.py                 # promoted from Bedrock__Chat__Engine (provider-neutral)
  provider/Chat__Provider.py             # the interface (the generalised source seam)
  provider/Chat__Provider__Registry.py   # self-registration, like AWS__Role__Profiles
  schemas/Schema__Chat__{Session,Message,Turn,Context,Document,Tool_Call,Usage}.py
  schemas/Schema__Chat__Model.py         # id, label, provider, ctx window, capabilities, pricing
  cost/Chat__Cost.py                     # tokens × per-model price; $0 / unknown handled
  widgets/Chat__{Bubble,Composer,Cost__Meter,Model__Picker,Provider__Picker}.py
  screens/Chat__Screen.py                # subclass of cli/tui Tui__App (Debug Panel free)
  cli/Cli__Tui__Chat.py                  # `sg tui chat` + list-providers / list-models
  tests/…                                # in-memory provider, no network

providers (each in its own home, implementing Chat__Provider):
  aws/bedrock/chat/Provider__Bedrock.py        # wraps existing Bedrock__Runtime__AWS__Client + Cost__Calculator + Model__Aliases
  cli/tui/chat/provider/Provider__Ollama.py    # local HTTP (http://localhost:11434/api/chat); $0
  cli/tui/chat/provider/Provider__OpenRouter.py# HTTPS (OpenAI-compatible /v1/chat/completions); API key
  cli/tui/chat/provider/Provider__In_Memory.py # scripted, for tests (promoted from Bedrock__Chat__In_Memory)
```

Bedrock-specific bits (`Bedrock__Model__Aliases/Resolver/Cost__Calculator/Region__Catalogue`,
the Nova pricing in `bedrock_chat_tui__config.py`) **stay** under `aws/bedrock/` and are
consumed by `Provider__Bedrock` only.

---

## 4. The provider interface (the heart of the work)

`Chat__Provider` (Type_Safe base) — one normalized contract, neutral message shape:

```python
class Chat__Provider(Type_Safe):
    def id(self) -> str: ...                          # 'bedrock' | 'ollama' | 'openrouter'
    def models(self) -> List__Schema__Chat__Model: ...# catalogue (id, label, ctx window, caps, price)
    def capabilities(self, model_id) -> Schema__Chat__Capabilities: ...  # streaming/tools/vision/json
    def stream_turn(self, model_id, messages, system=None, options=None): ...   # yields ('delta', text) | ('usage', Schema__Chat__Usage)
    def converse_turn(self, model_id, messages, system=None, tools=None, options=None) -> Schema__Chat__Turn__Result: ...
```

The normalization decisions (the real design effort):

- **Messages** — a neutral list `[{role: user|assistant|system, content: [text|image|tool_result]}]`.
  Each provider adapts it: Bedrock → converse `content:[{text}]`; Ollama / OpenRouter →
  OpenAI `[{role, content}]`. Adapters own the translation; the engine never sees a wire
  format. (Migration note: the engine's current `build_messages()` already emits the
  Bedrock shape — move that mapping *into* `Provider__Bedrock`.)
- **Usage** — `Schema__Chat__Usage(input_tokens, output_tokens, latency_ms)`. Bedrock
  reads the trailing `metadata` event; Ollama returns `prompt_eval_count` /
  `eval_count`; OpenRouter returns `usage{prompt_tokens, completion_tokens}`. Adapters
  normalize; if a backend omits tokens, `Chat__Cost` falls back to a char/4 estimate
  flagged "≈".
- **Tools** — neutral `Schema__Chat__Tool` (name, description, json_schema). Bedrock →
  `toolConfig`; OpenAI-style → `tools[]`. Tool-calling is the **hardest** normalization;
  ship chat-only first, add tools per-provider behind a capability flag (§6).
- **`options`** — a small neutral bag (temperature, max_tokens, top_p) so AWS `region`
  and Ollama `base_url` move into provider *config*, not the call signature.

---

## 5. Provider adapters

| Provider | Transport | Auth/config | Cost | Notes |
|----------|-----------|-------------|------|-------|
| **Bedrock** | boto3 `bedrock-runtime` | `Sg__Aws__Session.from_context()` (the chokepoint — transparent assume + auth guard already apply) | Nova prices × tokens (`Bedrock__Cost__Calculator`) | refactor existing source into `Chat__Provider`; no behaviour change |
| **Ollama** | HTTP `POST {base}/api/chat` (stream NDJSON) | `OLLAMA_HOST` / `--base-url` (default `http://localhost:11434`); **no auth** | **$0** (local) — cost meter shows tokens only | `models()` from `GET /api/tags`; great default for dev/offline |
| **OpenRouter** | HTTPS `POST /v1/chat/completions` (OpenAI-compatible, SSE stream) | API key from keyring (`Credentials__Store.secret_get('openrouter','api_key')`) or `OPENROUTER_API_KEY` | per-model USD from `GET /models` pricing (cache) | one HTTP client unlocks ~hundreds of models; OpenAI shape ⇒ adapter reusable for raw OpenAI later |
| **In-memory** | none | none | scripted | the test seam (promoted from `Bedrock__Chat__In_Memory`) |

HTTP providers use a single thin `Chat__HTTP__Client` boundary (the existing
`Inventory__HTTP__Client` pattern) so streaming + retries + the Debug feed live in one place.

---

## 6. Capabilities & graceful degradation

`Schema__Chat__Capabilities(streaming, tools, vision, json_mode, max_context)` per model.
The engine/screen consult it:
- no streaming → fall back to `converse_turn`, render the whole reply at once;
- no tools → the agentic loop is disabled, chat-only;
- the model picker greys models the active provider can't serve.
This is the same "capability-gated" idea as the SG/Edge Control Center (`can_act()`).

## 7. Cost, when there's a cost

`Chat__Cost` takes `(provider_id, model_id, usage)` → USD. Cloud models price from the
provider catalogue; **Ollama is $0**; unknown price → show tokens + "$ —". The budget
bar / per-turn cap (already in the engine) stay, but only bind when price > 0, so the
meter never nags on a free local model.

## 8. Provider registry & CLI

`Chat__Provider__Registry` mirrors `AWS__Role__Profiles`: providers self-register; the
CLI resolves `--provider`. Surface:

```
sg tui chat [--provider bedrock|ollama|openrouter] [--model <id|alias>]
            [--context-file F] [--base-url U] [--budget-usd N]
sg tui chat list-providers          # which are configured/reachable here
sg tui chat list-models [--provider P]
sg tui chat diagnose                # terminal + each provider's reachability/auth
```

`--provider` default: first configured & reachable (Ollama if up locally → Bedrock if AWS
creds → OpenRouter if key present), or an explicit `SG_TUI_CHAT__PROVIDER`.

## 9. Embedding & the TUI-API standard

Host TUIs (CF logs, sg-edge) embed the chat by building a `Schema__Chat__Context` and
launching `Chat__Screen` — exactly the CF-chat flow in `01__brief.md`. Per the TUI-API
brief, the chat both **consumes** host providers (`state()`/`export()` → context, and
later `dispatch()` as tools) and **exposes** its own `Tui_Api__Provider`
(session/cost/transcript queryable; actions send/clear/set-model/set-provider/export).

---

## 10. Slice plan

1. **C1 — promote the neutral core** to `cli/tui/chat/` (engine, session/message/turn/
   context schemas, the 3 widgets, in-memory provider). Bedrock tests stay green;
   `aws/bedrock/tui` imports from the new home. Pure move + the `Chat__Provider` seam.
2. **C2 — `Provider__Bedrock`** implements the interface over the existing Bedrock client/
   cost/aliases. `sg aws bedrock chat tui` now runs through the shared engine. No new caps.
3. **C3 — `Provider__Ollama`** (local, $0): `Chat__HTTP__Client`, `/api/chat` stream,
   `/api/tags` catalogue, `capabilities`. `sg tui chat --provider ollama`.
4. **C4 — `Provider__OpenRouter`**: OpenAI-compatible stream, key from keyring/env,
   pricing from `/models` (cached). Cost normalization across providers.
5. **C5 — provider registry + `sg tui chat` CLI** (list-providers/list-models/diagnose,
   default-provider resolution).
6. **C6 — tools/agentic normalization** (Bedrock toolConfig ↔ OpenAI tools), behind the
   capability flag — the hard part, last.

C1–C2 are pure refactor (high safety). C3 gives offline/local chat fast. C1–C5 deliver
"`sg tui chat` against any provider"; the CF-logs chat (`01__brief.md`) then sits on top.

## 11. Risks / open questions

1. **Tool-calling normalization** (Bedrock `toolConfig` vs OpenAI `tools`/`tool_calls`)
   is the genuine complexity — defer to C6, ship chat-first.
2. **Streaming shapes differ** (Bedrock events / Ollama NDJSON / OpenRouter SSE) — isolate
   in adapters; the engine only sees `('delta', text)` / `('usage', Usage)`.
3. **Secrets** — the OpenRouter key must live in the keyring (`secret_set`), never Git
   (CLAUDE.md #12/#13). `list-providers` reports "key missing" rather than failing hard.
4. **Pricing freshness** — OpenRouter prices change; cache `/models` with a TTL and a
   "prices as of …" label so cost is honest.
5. **Where does the neutral core live** — `cli/tui/chat/` (proposed) vs a new top-level
   package. `cli/tui/` already hosts the shared TUI framework, so it's the natural home.

## 12. Non-goals (first pass)

- No fine-tuning, no embeddings/RAG store (context is injected, not retrieved — yet).
- No persistence of sessions (ephemeral, as today).
- No raw-OpenAI/Anthropic-direct providers initially (OpenRouter covers those models);
  the OpenAI-shaped adapter makes adding them trivial later.
