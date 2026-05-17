---
title: "sg aws observe — User Guide"
file: 16__observe.md
author: Dev (Claude)
date: 2026-05-17
repo: SGraph-AI__Service__Playwright @ claude/aws-primitives-support-uNnZY
status: LANDED — v0.2.29 Slice H
---

# `sg aws observe` — Unified Observability REPL

Read-only observability surface across S3, CloudWatch Logs, and CloudTrail. All commands are read-only — no mutation gate required.

---

## Commands

### `sources` — list connected adapters

```bash
sg aws observe sources
sg aws observe sources --json
```

Lists all registered source adapters with connection status and stream count.

**JSON shape**

```json
[
  {"name": "s3",         "connected": true, "stream_count": 12, "last_event": ""},
  {"name": "cloudwatch", "connected": true, "stream_count": 5,  "last_event": ""},
  {"name": "cloudtrail", "connected": true, "stream_count": 1,  "last_event": ""}
]
```

---

### `tail` — stream recent entries

```bash
sg aws observe tail --source cloudwatch --stream /aws/lambda/my-fn --since 1h
sg aws observe tail --source s3 --stream my-bucket --since 30m --json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | Adapter name (`s3`, `cloudwatch`, `cloudtrail`) |
| `--stream` | `''` | Specific stream within the source (bucket, log group, trail) |
| `--since` | `1h` | Relative (`30s`, `5m`, `2h`, `1d`) or ISO 8601 UTC |
| `--json` | off | Machine-readable output |

---

### `query` — search events

```bash
sg aws observe query "ERROR" --source cloudwatch --since 24h --limit 50
sg aws observe query "PutObject" --source cloudtrail --json
```

| Arg/Flag | Default | Description |
|----------|---------|-------------|
| `<query_text>` | (required) | Filter/search text applied by each adapter |
| `--source` | `''` | Limit to one adapter; omit to query all |
| `--since` | `24h` | Time window |
| `--limit` | `100` | Max events returned per source |
| `--json` | off | Machine-readable output |

---

### `stats` — aggregate statistics

```bash
sg aws observe stats --source cloudwatch --stream /aws/lambda/my-fn --by count --since 24h
sg aws observe stats --source s3 --stream my-bucket --by count --json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | Adapter name |
| `--stream` | `''` | Specific stream |
| `--by` | (required) | Aggregation: `count`, `sum`, `avg`, `min`, `max`, `unique` |
| `--since` | `24h` | Time window |
| `--json` | off | Machine-readable output |

---

### `agent-trace` — cross-source session trace

```bash
sg aws observe agent-trace sess-abc-123
sg aws observe agent-trace sess-abc-123 --json
```

Queries all registered sources for events containing the session_id string. Useful for tracing an agent session across CloudWatch, S3, and CloudTrail in one shot.

**JSON shape**

```json
{
  "session_id":   "sess-abc-123",
  "total_events": 7,
  "by_source":    {"cloudwatch": 5, "cloudtrail": 2},
  "events":       [...]
}
```

---

### `replay` — replay a captured session

```bash
sg aws observe replay ~/.sg/aws/observe/sessions/sess-abc-123.jsonl
```

Replays events from a JSONL session file previously written by `Observe__Session__Writer`. Session files are stored at `~/.sg/aws/observe/sessions/` with permissions 0600.

---

## Source adapters

| Name | Backed by | Streams |
|------|-----------|---------|
| `s3` | `S3__AWS__Client` | S3 buckets |
| `cloudwatch` | `Logs__AWS__Client` (CloudWatch Logs) | Log groups |
| `cloudtrail` | `CloudTrail__AWS__Client` | Trails |

---

## What backs this

```
sgraph_ai_service_playwright__cli/aws/observe/
├── cli/Cli__Observe.py              ← Typer commands
├── sources/S3__Source__Adapter.py
├── sources/CloudWatch__Source__Adapter.py
├── sources/CloudTrail__Source__Adapter.py
├── Source__Registry.py
├── service/Observe__Session__Writer.py
├── service/Observe__Agent__Tracer.py
├── schemas/Schema__Observe__Source__Status.py
└── collections/List__Schema__Observe__Source__Status.py
```
