---
title: "v0.2.29 — sg aws bedrock (Slice E)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: XL — ~2800 prod lines, ~900 test lines, ~4 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_brief: team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__planning-brief__bedrock-cli-native-support.md
feature_branch: claude/aws-primitives-support-uNnZY-bedrock
---

# `sg aws bedrock` — Slice E

Bedrock absorbed into the type-safe SG `sg aws *` surface. **Scope locked to `chat` + `agent` + `tool` sub-trees.** `kb`, `guardrail`, `eval`, `observe`, `meta`, multi-agent collaboration, and payments are all explicitly deferred to a v0.2.30 follow-up pack.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/cli/` (look for `cli/aws-*.md`) before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone — the largest. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

Independent of all other v0.2.29 slices.

---

## Source brief

[`v0.27.43__planning-brief__bedrock-cli-native-support.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__planning-brief__bedrock-cli-native-support.md) is ground truth. It is a **planning brief** — by design, not all design decisions are settled. The locked decisions in the umbrella `README.md §5` carve the scope; the open questions in the source brief §"Open Questions For The Plan" remain and are addressed inline below where they impact implementation.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/bedrock/` (Foundation ships the skeleton; you fill in the bodies)

### Sub-trees

```
sg aws bedrock
├── chat
│   ├── claude        --prompt "..." [--model opus-4.7|sonnet-4.6|haiku-4.5] [--input file]
│   ├── nova          --prompt "..." [--model lite|pro|micro|premier]
│   ├── llama         --prompt "..." [--model 3.1|4-scout|4-maverick]
│   ├── openai        --prompt "..." [--model gpt-...]
│   ├── any           --prompt "..." --provider <name> [--model ...]
│   └── list-models   [--provider X]
├── agent
│   ├── create     --name X --model Y [--tools "browser,code-interpreter"] [--memory short|long|both]
│   ├── invoke     <name> --prompt "..." [--session <id>]
│   ├── list
│   ├── get        <name>
│   ├── stop       <session-id>
│   ├── memory list --agent X
│   ├── memory clear --agent X --scope short|long|both
│   └── tools add --agent X --gateway-tool <arn>
└── tool
    ├── browser session start [--region X]
    ├── browser session navigate <session-id> <url>
    ├── browser session click <session-id> <selector>
    ├── browser session screenshot <session-id> [--output file]
    ├── browser session stop <session-id>
    ├── browser session list
    ├── code-interpreter session start --language python|javascript|typescript
    ├── code-interpreter session run <session-id> --code "..." [--files file...]
    ├── code-interpreter session stop <session-id>
    └── code-interpreter session list
```

**Mutation gate:** `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` required for `agent {create,stop,memory clear,tools add}` and `tool * session {start,stop,navigate,click,run}`. `chat` is read-only (no gate); `agent invoke` is read-only on the agent definition but mutates session state — treat as mutating to be safe.

### Local-file grounding (vault deferred per locked decision #15)

Every call writes to a local file by default (unless `--no-capture`). Vault integration is explicitly out of scope for v0.2.29 (umbrella locked decision #15) — a future v0.3.x pack re-targets the writer to point at the canonical vault writer without changing the CLI contract.

| Output type | Local layout |
|-------------|--------------|
| `chat` interactions | `~/.sg/aws/bedrock/chat/<ISO-day>/<run-id>.json` — prompt + response + tokens + cost + model + region |
| `agent` definitions | `~/.sg/aws/bedrock/agents/<agent-name>/definition.json` (versioned by mtime-keyed copies) |
| `agent invoke` sessions | `~/.sg/aws/bedrock/agents/<agent-name>/sessions/<session-id>/...` — full trace |
| `agent` memory snapshots | `~/.sg/aws/bedrock/agents/<agent-name>/memory/<scope>/<snapshot-id>.json` |
| `tool browser` sessions | `~/.sg/aws/bedrock/tools/browser/<session-id>/...` — actions log + screenshots |
| `tool code-interpreter` sessions | `~/.sg/aws/bedrock/tools/code-interpreter/<session-id>/...` — code + stdout + stderr |

A central `Bedrock__Capture__Writer` (one class, used by every verb) enforces the layout. Files are written with `0600` perms (same convention as the v0.2.28 credentials store).

The class is intentionally writer-interface-shaped: when the v0.3.x vault re-introduction pack lands, swapping `Bedrock__Capture__Writer` for a `Bedrock__Vault__Writer` will be a constructor change at the call sites, not a verb-level rewrite.

### Model-ID resolution (per brief §"Critical detail")

A `Bedrock__Model__Resolver` class hides Bedrock's model-ID complexity:

- User says `claude`, `nova`, `llama`, `openai` → resolver returns the canonical model ID for the user's region + account
- User says `claude --model opus-4.7` → resolver picks the right inference profile (cross-region profile when needed, application inference profile when needed)
- Aliases live in a per-region YAML at `library/reference/v0.2.29__bedrock-model-aliases.yaml` (Foundation ships this; this slice maintains it)
- `list-models` reports what's enabled in the account/region, not the full Bedrock catalogue — data source is `boto3.client('bedrock').list_foundation_models()` (`bedrock` control-plane API, not `bedrock-runtime`), filtered to models in `byInferenceType IN ('ON_DEMAND','PROVISIONED')` for the active region. Wrapped by `Bedrock__Control__AWS__Client` honouring `Sg__Aws__Session`.

### SDK choice (per brief §"Open Questions" #7)

- **`chat`**: boto3 `bedrock-runtime` (low-risk, stable API). Wrapped by `Bedrock__Runtime__AWS__Client` honouring `Sg__Aws__Session`.
- **`agent`**: AgentCore SDK (`bedrock-agentcore` boto3 namespace + the AgentCore Python SDK where the boto3 surface gaps). Wrapped by `Bedrock__Agent__AWS__Client`.
- **`tool browser` and `tool code-interpreter`**: AgentCore SDK. Wrapped by `Bedrock__Tool__AWS__Client`.

If the AgentCore SDK has gaps that block `agent` or `tool`, **`chat` still ships** standalone and the `agent` / `tool` sub-trees are tagged `EXPERIMENTAL` in the user-guide. Defer the gaps to v0.2.30.

---

## Production files (indicative)

```
aws/bedrock/
├── cli/
│   ├── Cli__Bedrock.py
│   ├── chat/
│   │   ├── Cli__Bedrock__Chat.py
│   │   └── verbs/
│   │       ├── Verb__Bedrock__Chat__Claude.py
│   │       ├── Verb__Bedrock__Chat__Nova.py
│   │       ├── Verb__Bedrock__Chat__Llama.py
│   │       ├── Verb__Bedrock__Chat__Openai.py
│   │       ├── Verb__Bedrock__Chat__Any.py
│   │       └── Verb__Bedrock__Chat__List_Models.py
│   ├── agent/
│   │   ├── Cli__Bedrock__Agent.py
│   │   └── verbs/...
│   └── tool/
│       ├── Cli__Bedrock__Tool.py
│       ├── browser/verbs/...
│       └── code_interpreter/verbs/...
├── service/
│   ├── Bedrock__Runtime__AWS__Client.py    # boto3 bedrock-runtime
│   ├── Bedrock__Agent__AWS__Client.py      # AgentCore SDK
│   ├── Bedrock__Tool__AWS__Client.py       # AgentCore SDK
│   ├── Bedrock__Model__Resolver.py
│   ├── Bedrock__Capture__Writer.py         # local-file writer (vault deferred — locked decision #15)
│   ├── Bedrock__Stream__Adapter.py         # SSE → NDJSON for --json mode
│   └── Bedrock__Cost__Calculator.py        # tokens × per-region pricing
├── schemas/                                # Schema__Bedrock__Chat__Response, ...Agent__Definition, ...Tool__Session, ...Memory__Snapshot, etc.
├── enums/                                  # Enum__Bedrock__Provider, Enum__Bedrock__Memory__Scope, Enum__Bedrock__Tool__Type
├── primitives/                             # Safe_Str__Bedrock__Model_Id, Safe_Str__Bedrock__Agent_Arn, Safe_Str__Bedrock__Session_Id, etc.
└── collections/                            # List__Schema__Bedrock__Model, Dict__Bedrock__Memory, etc.
```

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned)
- `kb`, `guardrail`, `eval`, `observe`, `meta`, `multi-agent`, `payments` sub-trees — all deferred
- The credential-manager integration for routing API keys server-side (Slice G provides scoped credentials; Bedrock uses them automatically via `Sg__Aws__Session`)
- The MCP interop work — separate brief later
- The pre-auth payments metering integration — depends on the payments substrate landing first

---

## Acceptance

```bash
# chat
sg aws bedrock chat list-models                                        # → enabled models in current region
sg aws bedrock chat claude --prompt "What is 2+2?" --model haiku-4.5  # → response
sg aws bedrock chat nova --prompt "Summarise this:" --input README.md  # → response
sg aws bedrock chat any --provider anthropic --prompt "ping"

# chat with local-file capture (vault deferred — locked decision #15)
sg aws bedrock chat claude --prompt "hello"                            # → response; capture file appears
ls ~/.sg/aws/bedrock/chat/$(date +%Y-%m-%d)/                          # → at least one .json

# chat --json + streaming
sg aws bedrock chat claude --prompt "long answer" --stream --json | head -5  # → NDJSON chunks

# agent (gated)
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent create \
    --name researcher --model claude --tools "browser,code-interpreter" \
    --memory both --capture-path ~/.sg/aws/bedrock/agents/researcher --yes
sg aws bedrock agent list                                              # → researcher visible
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent invoke researcher \
    --prompt "Research X and report" --yes                             # → response; session captured to ~/.sg/aws/bedrock/agents/researcher/sessions/<id>/
sg aws bedrock agent memory list --agent researcher
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent stop <session-id> --yes

# tool (gated)
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session start --yes
sg aws bedrock tool browser session list                               # → session visible
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session navigate <id> https://example.com --yes
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session screenshot <id> --output /tmp/shot.png --yes
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session stop <id> --yes

SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session start --language python --yes
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session run <id> --code "print(2+2)" --yes
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session stop <id> --yes

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/ -v
SG_AWS__BEDROCK__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/bedrock/ -v
```

---

## Deliverables

1. All files under `aws/bedrock/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/` (no mocks; in-memory clients)
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/bedrock/` (gated; uses a real Bedrock account)
4. `library/reference/v0.2.29__bedrock-model-aliases.yaml` — per-region alias table
5. New user-guide page `library/docs/cli/sg-aws/13__bedrock.md` (~10 KB; split into chat/agent/tool sections)
6. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
7. Reality-doc update: new `team/roles/librarian/reality/cli/aws-bedrock.md`

---

## Risks to watch

- **Bedrock model availability changes by region and over time.** `list-models` must reflect what's actually enabled; refuse to invoke a model not present in the alias table for the resolved region.
- **Inference-profile complexity (planning brief §"Critical detail").** Opus 4.7 may only be available via cross-region inference profile; some models require ARN-versioned IDs. `Bedrock__Model__Resolver` owns this; it must be the only place that knows.
- **Streaming format.** SSE from Bedrock → NDJSON for `--json` mode. Confirm the contract matches the rest of the SG CLI conventions.
- **Cost surprises.** Every chat call logs a cost estimate. Hard cap per-call cost at `$SG_AWS__BEDROCK__MAX_CALL_COST` (default $1.00); refuse calls predicted to exceed it unless `--cost-override $X` passed.
- **AgentCore SDK availability gaps.** If the AgentCore Python SDK is missing surface area, `agent` and `tool` ship `EXPERIMENTAL` and degrade to "raises a clear `Not_Implemented__Awaiting__AgentCore_SDK` error in the broken codepath." `chat` is unaffected.
- **Vault writer overhead on long sessions.** Streaming sessions (tool browser, agent invoke) write incrementally; never buffer a full session in memory.
- **OpenAI on Bedrock is limited-preview.** Treat `openai` as best-effort; gate with `SG_AWS__BEDROCK__ALLOW_OPENAI_PREVIEW=1` to avoid surprise failures for users in non-preview accounts.

---

## Commit + PR

Branch: `v0.2.28__bedrock__uNnZY` (off `claude/aws-primitives-support-uNnZY` after Foundation merges)

Commit message: `feat(v0.2.29): sg aws bedrock — chat + agent + tool sub-trees with local-file capture`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

Independent. The biggest slice; the most likely candidate for partial descope. Two clean descope points:

1. **`chat`-only**: ship `chat` + `list-models`, drop `agent` and `tool` sub-trees. ~1/3 the size; preserves the user-visible value.
2. **Defer entirely**: archive this folder with `STATUS: DEFERRED — v0.2.30 pack`. No other v0.2.29 slice is affected.
