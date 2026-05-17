---
title: "Reality — sg aws bedrock (Slice E)"
file: aws-bedrock.md
domain: cli
author: Dev (Claude)
date: 2026-05-17
status: LIVE — v0.2.29 Slice E shipped
branch: claude/aws-primitives-support-uNnZY
---

# Reality: `sg aws bedrock`

## What exists

Production code: `sgraph_ai_service_playwright__cli/aws/bedrock/`

### Sub-trees

All three sub-trees are implemented:

| Sub-tree | Status |
|----------|--------|
| `chat` | LIVE — read-only; all verbs wired |
| `agent` | LIVE — EXPERIMENTAL; gated by `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` |
| `tool` | LIVE — EXPERIMENTAL; gated by `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` |

### Chat verbs

- `sg aws bedrock chat list-models [--provider X] [--json]` — ON_DEMAND models in current account/region
- `sg aws bedrock chat claude --prompt TEXT [--model ALIAS] [--input FILE] [--stream] [--json] [--cost-override N]`
- `sg aws bedrock chat nova --prompt TEXT [--model ALIAS] [--input FILE] [--json]`
- `sg aws bedrock chat llama --prompt TEXT [--model ALIAS] [--input FILE] [--json]`
- `sg aws bedrock chat any --prompt TEXT --provider PROVIDER [--model ALIAS] [--json]`

### Agent verbs (EXPERIMENTAL)

- `sg aws bedrock agent create --name X --model Y [--tools CSV] [--memory SCOPE] [--yes]`
- `sg aws bedrock agent invoke AGENT-ID --prompt TEXT [--session ID] [--alias ID] [--yes]`
- `sg aws bedrock agent list [--json]`
- `sg aws bedrock agent get AGENT-ID [--json]`
- `sg aws bedrock agent stop SESSION-ID --agent AGENT-ID [--alias ID] [--yes]`
- `sg aws bedrock agent memory list --agent X [--json]`
- `sg aws bedrock agent memory clear --agent X --scope SCOPE [--yes]`

### Tool verbs (EXPERIMENTAL)

- `sg aws bedrock tool browser session start [--region R] [--yes]`
- `sg aws bedrock tool browser session list [--json]`
- `sg aws bedrock tool browser session navigate SESSION URL [--yes]`
- `sg aws bedrock tool browser session screenshot SESSION [--output F] [--yes]`
- `sg aws bedrock tool browser session stop SESSION [--yes]`
- `sg aws bedrock tool code-interpreter session start [--language L] [--yes]`
- `sg aws bedrock tool code-interpreter session run SESSION --code TEXT [--yes]`
- `sg aws bedrock tool code-interpreter session stop SESSION [--yes]`
- `sg aws bedrock tool code-interpreter session list [--json]`

## Service classes

| Class | File | Role |
|-------|------|------|
| `Bedrock__Control__AWS__Client` | `service/` | boto3 `bedrock` control-plane — list-models |
| `Bedrock__Runtime__AWS__Client` | `service/` | boto3 `bedrock-runtime` — converse, stream |
| `Bedrock__Agent__AWS__Client` | `service/` | boto3 `bedrock-agent` / `bedrock-agent-runtime` |
| `Bedrock__Tool__AWS__Client` | `service/` | boto3 `bedrock-agentcore` — browser, code-interpreter |
| `Bedrock__Model__Resolver` | `service/` | YAML alias → canonical model ID |
| `Bedrock__Capture__Writer` | `service/` | Local `~/.sg/aws/bedrock/` capture; 0600 perms |
| `Bedrock__Cost__Calculator` | `service/` | Token × pricing → USD estimate + cap |
| `Bedrock__Stream__Adapter` | `service/` | SSE events → NDJSON |

## Schemas / Enums / Primitives

| Type | File |
|------|------|
| `Schema__Bedrock__Chat__Response` | `schemas/` |
| `Schema__Bedrock__Model` | `schemas/` |
| `Schema__Bedrock__Agent` | `schemas/` |
| `Schema__Bedrock__Tool__Session` | `schemas/` |
| `Enum__Bedrock__Provider` | `enums/` |
| `Enum__Bedrock__Memory__Scope` | `enums/` |
| `Enum__Bedrock__Tool__Type` | `enums/` |
| `Safe_Str__Bedrock__Model_Id` | `primitives/` |
| `Safe_Str__Bedrock__Agent_Arn` | `primitives/` |
| `Safe_Str__Bedrock__Session_Id` | `primitives/` |
| `List__Schema__Bedrock__Model` | `collections/` |
| `List__Schema__Bedrock__Agent` | `collections/` |
| `List__Schema__Bedrock__Tool__Session` | `collections/` |

## Tests

Unit tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/service/` — 79 tests, all passing.

Covers: model resolver (resolution, region overrides, alias list, provider enum), cost calculator (pricing table, cap, env override), capture writer (layout, content, 0600 perms), runtime client (converse, stream, text/usage extraction), control client (list models, infer provider), chat flow end-to-end (schema shape, capture, alias resolution, mutation gate absent for chat).

## References

- Alias YAML: `library/reference/v0.2.29__bedrock-model-aliases.yaml`
- User guide: `library/docs/cli/sg-aws/13__bedrock.md`
- Dev pack brief: `library/dev_packs/v0.2.29__sg-aws-bedrock/README.md`

## Limitations and deferred items

- **Vault integration** — deferred (umbrella locked decision #15). Use `~/.sg/aws/bedrock/` only.
- **AgentCore Python SDK** — not yet generally available. `agent` and `tool` sub-trees use boto3 `bedrock-agent` / `bedrock-agentcore` namespaces; raise `RuntimeError` for missing surface.
- **OpenAI on Bedrock** — limited-preview; gate with `SG_AWS__BEDROCK__ALLOW_OPENAI_PREVIEW=1` (not implemented; verb `chat any --provider openai` will fail in non-preview accounts).
- **Streaming cost accounting** — stream calls log `input_tokens=0, output_tokens=0` because Bedrock's `converse_stream` does not return a usage block in every event; full usage summary event not yet extracted.
- **`kb`, `guardrail`, `eval`, `observe`, `meta`, `multi-agent`, `payments`** — all deferred to v0.2.30.
