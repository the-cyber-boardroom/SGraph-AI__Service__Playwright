---
title: "sg aws bedrock — User Guide"
file: 13__bedrock.md
author: Dev (Claude)
date: 2026-05-17
status: LIVE — Slice E implementation
version: v0.2.29
---

# `sg aws bedrock` — User Guide

AWS Bedrock integration for the `sg aws *` CLI surface. Three sub-trees:

- **`chat`** — read-only; invoke foundation models; local capture; no mutation gate.
- **`agent`** — EXPERIMENTAL; AgentCore agent lifecycle; gated by `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1`.
- **`tool`** — EXPERIMENTAL; AgentCore inline browser and code-interpreter tools; gated.

All interactions write a local capture file under `~/.sg/aws/bedrock/` (vault integration is deferred — locked decision #15 of the v0.2.29 umbrella brief).

---

## Prerequisites

Standard AWS credential chain applies (`AWS_PROFILE`, `~/.aws/credentials`, env vars, IMDS). The Bedrock service must be enabled in your account and region.

```bash
# Verify credentials resolve
sg aws bedrock chat list-models
```

---

## Chat sub-tree

Chat is **read-only** — no mutation gate required.

### `list-models`

```bash
sg aws bedrock chat list-models
sg aws bedrock chat list-models --provider Anthropic
sg aws bedrock chat list-models --json
```

Lists foundation models enabled for **ON_DEMAND** inference in the current account/region. Data comes from the Bedrock control-plane `ListFoundationModels` API.

Flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--provider X` | all | Filter by provider name (e.g. Anthropic, Amazon, Meta). |
| `--json` | off | Output JSON array. |

### `claude`

```bash
sg aws bedrock chat claude --prompt "What is 2+2?"
sg aws bedrock chat claude --prompt "Explain X" --model haiku-4.5
sg aws bedrock chat claude --prompt "Summarise:" --input README.md --json
sg aws bedrock chat claude --prompt "Long answer" --stream --json | head -5
sg aws bedrock chat claude --prompt "Big job" --cost-override 5.00
```

Supported `--model` aliases (resolved by `Bedrock__Model__Resolver`):

| Alias | Bedrock model ID |
|-------|-----------------|
| `default` | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| `haiku-4.5` | `anthropic.claude-haiku-4-5:0` |
| `haiku-3.5` | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| `haiku-3` | `anthropic.claude-3-haiku-20240307-v1:0` |
| `sonnet-4.6` | `anthropic.claude-sonnet-4-6:0` |
| `sonnet-3.7` | `anthropic.claude-3-7-sonnet-20250219-v1:0` |
| `sonnet-3.5` | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `opus-4.7` | `us.anthropic.claude-opus-4-7:0` (cross-region profile) |

Full alias table: `library/reference/v0.2.29__bedrock-model-aliases.yaml`.

Flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt TEXT` | required | Prompt text. |
| `--model ALIAS` | `default` | Model alias. |
| `--input FILE` | none | File content appended to prompt. |
| `--stream` | off | Stream response chunks as NDJSON (use with `--json`). |
| `--json` | off | Machine-readable JSON output. |
| `--cost-override N` | none | Override per-call cost cap (USD). |

### `nova`

```bash
sg aws bedrock chat nova --prompt "Summarise this:" --input README.md
sg aws bedrock chat nova --prompt "Quick answer" --model micro
```

`--model` aliases: `lite` (default), `pro`, `micro`, `premier`.

### `llama`

```bash
sg aws bedrock chat llama --prompt "Explain recursion"
sg aws bedrock chat llama --prompt "Code review" --model 4-maverick
```

`--model` aliases: `default` (3.1 8B), `3.1`, `3.2`, `4-scout`, `4-maverick`.

### `any`

```bash
sg aws bedrock chat any --provider anthropic --prompt "ping"
sg aws bedrock chat any --provider nova --model pro --prompt "hello"
```

Generic escape hatch — pass any provider key from the alias table.

---

## Local capture

Every chat call writes a capture file:

```
~/.sg/aws/bedrock/chat/<ISO-day>/<run-id>.json
```

Content: prompt, response text, token counts, estimated cost, model ID, region, run ID.

Files are written with `0600` permissions (owner-only).

```bash
# See today's captures
ls ~/.sg/aws/bedrock/chat/$(date +%Y-%m-%d)/
cat ~/.sg/aws/bedrock/chat/$(date +%Y-%m-%d)/*.json | jq '.cost_usd'
```

### Cost cap

Every call estimates cost before execution. The default cap is **$1.00 per call**. Override:

```bash
export SG_AWS__BEDROCK__MAX_CALL_COST=5.00
# or per-call:
sg aws bedrock chat claude --prompt "..." --cost-override 5.00
```

---

## Agent sub-tree — EXPERIMENTAL

> **EXPERIMENTAL** — requires the boto3 `bedrock-agent` / `bedrock-agent-runtime` surface. Full AgentCore Python SDK (`bedrock-agentcore`) is not yet generally available. When gaps are hit, a clear error is raised.

All mutating commands require:

```bash
export SG_AWS__BEDROCK__ALLOW_MUTATIONS=1
```

### `agent create`

```bash
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent create \
    --name researcher \
    --model claude \
    --tools "browser,code-interpreter" \
    --memory both \
    --yes
```

Flags: `--name`, `--model` (alias or raw ID), `--tools` (CSV), `--memory` (short/long/both/none), `--yes`, `--json`.

Agent definition is captured to `~/.sg/aws/bedrock/agents/<name>/definition.json`.

### `agent list`

```bash
sg aws bedrock agent list
sg aws bedrock agent list --json
```

### `agent get`

```bash
sg aws bedrock agent get <agent-id>
```

### `agent invoke`

```bash
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent invoke <agent-id> \
    --prompt "Research topic X and report findings" \
    --yes
```

Session trace captured to `~/.sg/aws/bedrock/agents/<name>/sessions/<session-id>/trace.json`.

### `agent stop`

```bash
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent stop <session-id> \
    --agent <agent-id> --yes
```

### `agent memory list`

```bash
sg aws bedrock agent memory list --agent researcher
```

### `agent memory clear`

```bash
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock agent memory clear \
    --agent researcher --scope both --yes
```

---

## Tool sub-tree — EXPERIMENTAL

> **EXPERIMENTAL** — requires AgentCore SDK. All session-mutating commands are gated.

### Browser sessions

```bash
# Start
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session start --yes

# List
sg aws bedrock tool browser session list

# Navigate
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session navigate <id> https://example.com --yes

# Screenshot
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session screenshot <id> --output /tmp/shot.png --yes

# Stop
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool browser session stop <id> --yes
```

Session artefacts captured to `~/.sg/aws/bedrock/tools/browser/<session-id>/`.

### Code-interpreter sessions

```bash
# Start (default: python)
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session start --language python --yes

# List
sg aws bedrock tool code-interpreter session list

# Run code
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session run <id> \
    --code "print(2+2)" --yes

# Stop
SG_AWS__BEDROCK__ALLOW_MUTATIONS=1 sg aws bedrock tool code-interpreter session stop <id> --yes
```

Session artefacts captured to `~/.sg/aws/bedrock/tools/code-interpreter/<session-id>/`.

---

## Mutation gate summary

| Sub-tree / verb | Gate required |
|-----------------|---------------|
| `chat *` | No |
| `agent list / get / memory list` | No |
| `agent create / invoke / stop / memory clear` | `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` |
| `tool * session list` | No |
| `tool * session start / navigate / screenshot / run / stop` | `SG_AWS__BEDROCK__ALLOW_MUTATIONS=1` |

---

## Backing service classes

| Class | API surface |
|-------|-------------|
| `Bedrock__Control__AWS__Client` | boto3 `bedrock` — list-models |
| `Bedrock__Runtime__AWS__Client` | boto3 `bedrock-runtime` — converse, converse_stream |
| `Bedrock__Agent__AWS__Client` | boto3 `bedrock-agent` / `bedrock-agent-runtime` — agents |
| `Bedrock__Tool__AWS__Client` | boto3 `bedrock-agentcore` — browser, code-interpreter |
| `Bedrock__Model__Resolver` | YAML alias table → canonical model ID |
| `Bedrock__Capture__Writer` | Local capture to `~/.sg/aws/bedrock/` (0600 perms) |
| `Bedrock__Cost__Calculator` | Token × per-model pricing → USD estimate |
| `Bedrock__Stream__Adapter` | SSE events → NDJSON lines |

Source: `sgraph_ai_service_playwright__cli/aws/bedrock/`

---

## FAQ

**Why is `bedrock-agentcore` not available?**
The AgentCore Python SDK has not been released publicly. This surface falls back to boto3 `bedrock-agent` and raises `RuntimeError` for methods that have no boto3 equivalent. Watch for SDK availability updates.

**Where is the vault integration?**
Vault integration is explicitly deferred (v0.2.29 umbrella locked decision #15). Local file capture is intentionally writer-interface-shaped so a future vault writer swap is a single constructor change.

**How do I change the capture root?**
`Bedrock__Capture__Writer` accepts a `root` constructor argument. The CLI always uses the default `~/.sg/aws/bedrock/` (override via subclassing for tests or custom deploy targets).

**Why does Opus 4.7 use a cross-region profile?**
Opus 4.7 is only available via inference profiles in most regions. `Bedrock__Model__Resolver` handles the region-specific profile selection automatically — the user just passes `--model opus-4.7`.
