---
title: "sg aws lambda — Lambda function management"
file: 07__lambda.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 07 — `sg aws lambda`

Lambda function discovery, configuration, logs, invocations, deployment, and Function-URL management.

**Mutation gate:** `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` required for `deploy`, `delete`, `url create/delete`.

---

## Command shape

```
sg aws lambda list                              ← list all functions in region
sg aws lambda <function-name> <verb> [opts]     ← per-function verb
```

`<function-name>` accepts a **fuzzy substring**. e.g.:

```bash
sg aws lambda waker info
# → resolves to sg-compute-vault-publish-waker-prod  (cached 5 min)
```

Fuzzy resolution is implemented by `Lambda__Name__Resolver`. If two functions match the substring you get an error listing both — disambiguate with a longer substring.

---

## `list`

Every function in the account/region.

```bash
sg aws lambda list
sg aws lambda list --runtime python3.12
sg aws lambda list --json | jq '.[] | .name'
```

**Flags:** `--runtime RUNTIME`, `--json`.

---

## `<name> info`

Headline metadata: ARN, runtime, state, memory, timeout, code size, last-modified, Function URL (if any).

```bash
sg aws lambda waker info
sg aws lambda waker info --json
```

---

## `<name> details`

Full function configuration — env vars, layers, VPC config, dead-letter, snap-start, tracing, etc.

```bash
sg aws lambda waker details
```

---

## `<name> config`

Show / manage configuration knobs (memory, timeout, env vars, layers). Read-only display by default; mutations are part of the wider config verb-set.

```bash
sg aws lambda waker config
```

---

## `<name> logs`

CloudWatch Logs viewer for the function's log group. Tail-mode (`--tail`) polls for new events; non-tail mode pulls a historical window.

```bash
# last 5 minutes, then exit
sg aws lambda waker logs --since 5m

# tail forever
sg aws lambda waker logs --tail

# historical window with filter
sg aws lambda waker logs --since 2h --filter "ERROR"

# narrow to one log stream prefix (cold-start streams etc.)
sg aws lambda waker logs --stream 2026/05/17 --since 1h
```

**Flags:**
- `--since TIME` — `30s`, `5m`, `2h`, `1d`, or ISO UTC. Default behaviour is `now - 5m` if not passed.
- `--until TIME` — same format
- `--filter PATTERN` — CloudWatch Logs filter syntax (`"ERROR"`, `"{$.level=\"error\"}"`, etc.)
- `--stream PREFIX` — restrict to one log-stream-name prefix
- `--tail` — poll forever
- `--limit N` — max events (default 100, ignored under `--tail`)
- `--poll-interval MS` — tail poll period (default 2000)
- `--json`

---

## `<name> invocations`

Recent invocations summary built from CloudWatch metrics + Logs Insights.

```bash
sg aws lambda waker invocations
sg aws lambda waker invocations --json
```

---

## `<name> invoke`

Synchronous invocation.

```bash
sg aws lambda waker invoke --payload '{"slug":"sara-cv"}'
sg aws lambda waker invoke --async  --payload '{"event":"warm"}'
```

**Flags:** `--payload JSON` (or piped via stdin), `--async`, `--json`.

---

## `<name> deploy`  ⚠ mutates

Create / update the function from a local code directory.

```bash
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 \
  sg aws lambda waker deploy \
    --code-path ./lambda_code \
    --handler   index.handler \
    --runtime   python3.12 \
    --memory    512 \
    --timeout   60 \
    --yes
```

**Flags:**
- `--code-path PATH` (required) — folder to zip and upload
- `--handler HANDLER` (required) — `module.function` entry-point
- `--role-arn ARN` — execution-role ARN
- `--runtime RUNTIME` — default `python3.11`
- `--memory MB` — default 256
- `--timeout SEC` — default 900
- `--json`, `--yes`

---

## `<name> delete`  ⚠ mutates

```bash
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 sg aws lambda waker delete --yes
```

---

## `<name> url` — Function URL subgroup

A Lambda Function URL is the HTTPS endpoint that fronts the function (no API Gateway).

### `<name> url show`

```bash
sg aws lambda waker url show
sg aws lambda waker url show --json
```

### `<name> url create`  ⚠ mutates

```bash
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 \
  sg aws lambda waker url create --auth-type NONE
```

**Flags:** `--auth-type {NONE|AWS_IAM}` (default `NONE`).

### `<name> url delete`  ⚠ mutates

```bash
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 sg aws lambda waker url delete
```

---

## `<name> tags / versions / aliases`

Three lighter subgroups for tagging, version pinning, and alias management. Run `--help` on each for the current flag set — these surfaces are still in active expansion.

```bash
sg aws lambda waker tags
sg aws lambda waker versions
sg aws lambda waker aliases
```

---

## Patterns

**"Did the last deploy take?":**

```bash
sg aws lambda waker info
sg aws lambda waker logs --since 30m --filter "INIT_START"
```

**"What's the cold-start time?":**

```bash
sg aws lambda waker logs --since 1h --filter "Init Duration"
```

**"Deploy + tail logs":**

```bash
SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 \
  sg aws lambda waker deploy --code-path ./lambda_code --handler app.handler --yes && \
sg aws lambda waker logs --tail
```

---

## What backs this

Code at `sgraph_ai_service_playwright__cli/aws/lambda_/`:

| Class | What it does |
|-------|-------------|
| `Lambda__AWS__Client` | boto3 wrapper — list / get / CRUD / invoke / URL ops |
| `Lambda__Name__Resolver` | Fuzzy substring → exact function name (cached 5 min) |
| `Lambda__Deployer` | Zip-from-folder + create-or-update orchestration |
| `Lambda__Invocations__Reporter` | CloudWatch metrics + Logs Insights summary |

CloudWatch Logs is fronted by `aws/logs/service/Logs__AWS__Client` — wired into `<name> logs` only; there's no `sg aws logs` top-level group today.

The dynamic Click group (`Lambda__App__Group` in `aws/lambda_/cli/`) is what allows the `<function-name>` substring to be resolved at command-parse time. That's why `lambda` is injected into `sg aws` differently from the other groups in `Cli__Aws.py`.

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/lambda_/`.
