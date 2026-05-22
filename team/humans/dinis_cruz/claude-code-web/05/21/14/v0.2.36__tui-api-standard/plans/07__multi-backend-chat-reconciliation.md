---
title: "Multi-backend chat — the Chat__Backend seam that preserves tools/documents/agentic"
file: 07__multi-backend-chat-reconciliation.md
author: Architect (Claude)
date: 2026-05-22 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — reconciliation. Responds to dev's `team/comms/plans/v0.2.41__cf-logs-tui-chat/02`.
parent:
  - "team/comms/plans/v0.2.41__cf-logs-tui-chat/02__shared-tui-chat-multi-provider.md (on dev — the multi-provider plan)"
  - 01__tui-api-contract-and-conventions.md
  - "aws/bedrock/tui/ — the built chat (engine, agentic loop, tools, documents, inspector) on THIS branch"
---

# Multi-backend chat — reconciling plan 02 with the built agentic chat

> Plan 02 (on dev) generalises the chat to **multiple model backends** (Bedrock / Ollama /
> OpenRouter). It was written against the *base* v0.2.36 chat. **This branch** has since
> added the agentic tool loop, tools, documents, the loadout, the execution center, the
> inspector tool-cards, and the honest-result path — all on the same files plan 02 would
> promote. This doc specifies the seam so the generalisation **preserves** those
> capabilities instead of regressing to chat-only.

---

## 1. Two layers, two "providers" (rename one)

The chat has **two** plug-points; plan 02 and the standard each generalise one:

| Layer | What plugs in | Interface | Generalised by |
|---|---|---|---|
| **Model backend** | the LLM (Bedrock / Ollama / OpenRouter) | **`Chat__Backend`** | plan 02 |
| **Tool provider** | a capability (VFS / web / s3 / the host TUI) | `Tui_Api__Provider` | the standard (built) |

> **Rename:** plan 02's `Chat__Provider` → **`Chat__Backend`**. Reserve "provider" for
> `Tui_Api__Provider` (tools). Mental model: **the chat talks to one model *backend* and
> many tool *providers*.** This removes the collision and clarifies the whole design.

---

## 2. What the seam MUST preserve (built on this branch)

These already work and touch the files plan 02 promotes — the `Chat__Backend` seam has to
carry all of them, not just `stream_turn`:

- **Streaming** chat (`send_turn` + `stream_turn`).
- **Non-streaming converse** with a `stopReason` (`converse_turn`) — the agentic loop needs it.
- **The agentic tool loop** (`send_turn_agentic`): converse → `tool_use` → execution center → `tool_result` → repeat.
- **Tools**: `Bedrock__Tool_Config__Builder` (actions → `toolConfig` + name→action map), routed through the execution center (gated/audited).
- **Documents**: `build_messages` emits Converse `document` blocks; `send_turn(documents=…)`.
- **Usage/cost**: exact tokens from the metadata event → `Bedrock__Cost__Calculator`; per-turn `model_calls`/`tool_calls`/`tool_log`.
- **Honest results**: a gated/failed tool feeds its real error back (no false success).

The key realisation: **the agentic loop must move to the NEUTRAL layer, and the
Bedrock wire-shaping must move INTO the Bedrock backend.** Today both live in the engine.

---

## 3. The neutral data model (Type_Safe)

The engine speaks only these; each backend adapts to its wire format:

```python
Schema__Chat__Message:                                   # role + neutral content blocks
    role    : Enum(user|assistant|system)
    content : List[Schema__Chat__Content]

Schema__Chat__Content:                                   # one block — exactly one of:
    text        : str = ''
    document    : Schema__Chat__Document = None           # {name, format, data_b64}
    tool_use    : Schema__Chat__Tool_Use = None           # {id, name, input}
    tool_result : Schema__Chat__Tool_Result = None        # {id, status, json}

Schema__Chat__Tool:                                      # a neutral tool offered to the model
    name        : str                                     # sanitised [a-zA-Z0-9_-]{1,64} — valid for Bedrock AND OpenAI
    description : str
    input_schema: dict                                    # JSON Schema (from Tui_Api__Schema__Builder)

Schema__Chat__Usage:        input_tokens · output_tokens · latency_ms · estimated: bool
Schema__Chat__Turn__Result: stop_reason(end_turn|tool_use) · content: List[Schema__Chat__Content] · usage
```

Tool **names + the name→(slug,action) map stay neutral** at the engine/loadout layer (the
existing sanitiser already produces names valid on both Bedrock and OpenAI). Backends adapt
only the *shape*, never the names.

---

## 4. The `Chat__Backend` interface

```python
class Chat__Backend(Type_Safe):                          # one model backend
    def id(self)                       -> str                                    # 'bedrock' | 'ollama' | 'openrouter'
    def models(self)                   -> list                                   # [Schema__Chat__Model]
    def capabilities(self, model_id)   -> Schema__Chat__Capabilities             # streaming / tools / documents / vision / max_ctx
    def stream_turn(self, model_id, messages, system=None, options=None):        # yields ('delta', text) | ('usage', Schema__Chat__Usage)
        ...
    def converse(self, model_id, messages, system=None, tools=None, options=None) -> Schema__Chat__Turn__Result:
        ...                                                                      # tool-aware, non-streaming — the agentic loop's call
```

- `messages` / `tools` / the returned `content` are **neutral** (§3). No `region`, no
  Bedrock `toolConfig`, no Bedrock content blocks in the signature.
- `options` is a small neutral bag (temperature, max_tokens). AWS `region`, Ollama
  `base_url`, the OpenRouter key live in **backend config**, not the call.

---

## 5. Where the Bedrock wire-shaping goes (into `Chat__Backend__Bedrock`)

Everything Bedrock-specific that today lives in the engine moves into the backend adapter —
**behaviour-preserving**, just relocated:

| Today (engine / shared) | After (inside `Chat__Backend__Bedrock`) |
|---|---|
| `build_messages()` → Converse `content:[{text},{document}]` | adapter: neutral messages → Converse blocks (incl. documents) |
| `Bedrock__Tool_Config__Builder` (neutral tools → `toolConfig`) | adapter: neutral `tools` → `toolConfig.tools[*].toolSpec` |
| parse `toolUse` blocks from the response | adapter: Converse `toolUse` → neutral `tool_use` |
| emit `toolResult` blocks | adapter: neutral `tool_result` → Converse `toolResult` |
| usage from the metadata event; Nova pricing | adapter + `Bedrock__Cost__Calculator` (Nova) |

`Provider__Ollama` / `Provider__OpenRouter` do the **same adaptations to the OpenAI shape**
(`messages[]`, `tools[*].function`, `tool_calls`, `usage{prompt,completion}`). The neutral
contract is identical; only the adapters differ.

---

## 6. The engine, neutralised (preserves the agentic loop)

`Chat__Engine` (promoted, backend-neutral) keeps both paths — now in neutral terms:

```python
def send_turn(self, session, text, documents=None, on_delta=None):               # streaming chat
    # build neutral messages (text + neutral document blocks); backend.stream_turn(...)

def send_turn_agentic(self, session, text, registry, center, loadout, grants=None, documents=None):
    tools = self.tool_specs(loadout, registry)                                   # neutral [Schema__Chat__Tool] + name_map
    messages = self.build_neutral_messages(session)
    while steps:
        result = self.backend.converse(model_id, messages, system, tools=tools)  # ← backend adapts shape
        messages.append(assistant(result.content))
        if result.stop_reason != 'tool_use': break
        for block in result.content:                                             # NEUTRAL tool_use blocks
            if block.tool_use:
                slug, action = name_map[block.tool_use.name]
                r = center.execute(slug, action, block.tool_use.input, grants=grants)
                messages.append(user_tool_result(block.tool_use.id, r))          # neutral tool_result (honest on failure)
```

The loop reads/writes **neutral** `tool_use`/`tool_result`; the execution center, loadout,
name_map, `tool_log`, cost-summing, and honest-result behaviour are **unchanged** — they
were already provider-neutral (they operate on the TUI API contract, not on Bedrock). Only
the model call goes through the backend adapter.

---

## 7. Capability gating (per backend)

`Schema__Chat__Capabilities(streaming, tools, documents, vision, max_ctx)`:
- no `tools` → `send_turn_agentic` is unavailable; the loadout `^G` greys tools for that backend.
- no `documents` → `^D` attach is disabled (or the adapter inlines small text docs).
- no `streaming` → `send_turn` falls back to `converse` and renders the whole reply.
- Ollama: `tools` only on tool-capable local models; `documents` usually off → gate accordingly.

---

## 8. Migration map (so plan 02's C1/C2 land *on top of*, not against, this branch)

| Move | From | To |
|---|---|---|
| Engine (neutral) | `aws/bedrock/tui/service/Bedrock__Chat__Engine` | `cli/tui/chat/engine/Chat__Engine` |
| Session/Message/Turn/Document/Tool_Call schemas (neutralised) | `aws/bedrock/tui/schemas/` | `cli/tui/chat/schemas/` |
| The 3 widgets + inspector + tool-cards + vfs browser + doc chips | `aws/bedrock/tui/screens/` | `cli/tui/chat/widgets|screens/` |
| In-memory source | `Bedrock__Chat__In_Memory` | `cli/tui/chat/backend/Chat__Backend__In_Memory` |
| **Bedrock wire-shaping** (build_messages, toolConfig builder, toolUse/result, Nova cost) | the engine + `aws/bedrock/tui/tui_api/` | `aws/bedrock/chat/Chat__Backend__Bedrock` |
| Tool-spec building (neutral) | `Bedrock__Tool_Config__Builder` (the schema half) | `cli/tui/chat/Chat__Tool__Builder` (neutral) |
| Tools / loadout / execution center / VFS / web (unchanged) | `cli/tui/tool_api/` | **stay** — they're already neutral |

**Sequencing:** merge this branch to dev **first** (it carries the agentic/tools/documents
work), *then* run plan 02's C1 (promote + introduce `Chat__Backend`) as a behaviour-preserving
refactor on top. C2 = `Chat__Backend__Bedrock` (relocate the shaping). C3/C4 = Ollama/OpenRouter
adapters. Plan 02's "C6 tools last" is then **not** a from-scratch build — it's "implement the
tool adapters for the non-Bedrock backends," because the neutral loop already exists here.

---

## 9. Open questions

| # | Question | Lean |
|---|---|---|
| 1 | Neutral message — keep `documents` as a content block? | **Yes** (this branch attaches them); backends adapt or drop per capability. |
| 2 | Where does `Chat__Tool__Builder` (neutral tool specs) live? | `cli/tui/chat/` — it's backend-neutral; backends wrap the shape. |
| 3 | Do we neutralise `region`/`model_alias` off the session now? | Yes — session holds a neutral `model_id`; `region` → Bedrock backend config. |
| 4 | Merge-then-refactor vs refactor-on-dev-then-merge | **Merge this branch first**, then refactor — avoids a 3-way rewrite of the same files. |
| 5 | OpenRouter/Ollama tool-calling parity | Gate via capabilities; ship chat + Bedrock-tools first, add OpenAI-shape tool adapters next. |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
