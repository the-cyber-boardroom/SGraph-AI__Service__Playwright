---
title: "Reality — sg aws observe (Slice H, v0.2.29)"
file: aws-observe.md
domain: cli
author: Librarian (Claude)
date: 2026-05-17
status: LANDED — v0.2.29; updated v0.2.30 Open-2 (typed primitives)
---

# `sg aws observe` — Reality Doc

**Status:** LANDED — v0.2.29 Slice H
**Branch:** `claude/aws-primitives-support-uNnZY`
**Commit:** backfill after PR merge

---

## What exists

### CLI surface

`sgraph_ai_service_playwright__cli/aws/observe/cli/Cli__Observe.py`

Commands (all read-only — no mutation gate):

| Command | Flags |
|---------|-------|
| `sources` | `--json` |
| `tail` | `--source`, `--stream`, `--since 1h`, `--json` |
| `query <text>` | `--source`, `--since 24h`, `--limit 100`, `--json` |
| `stats` | `--source`, `--stream`, `--by`, `--since 24h`, `--json` |
| `agent-trace <session_id>` | `--json` |
| `replay <session_file>` | |

### Source adapters

| File | Backed by | Streams |
|------|-----------|---------|
| `sources/S3__Source__Adapter.py` | `S3__AWS__Client` (stub, Slice A) | S3 buckets |
| `sources/CloudWatch__Source__Adapter.py` | `Logs__AWS__Client` | Log groups |
| `sources/CloudTrail__Source__Adapter.py` | `CloudTrail__AWS__Client` (stub, Slice F) | Trails |

### Registry

`Source__Registry.py` — `register(name, adapter)`, `list_sources()`, `get_source(name)`, `source_names()`

### Service layer

| File | Purpose |
|------|---------|
| `service/Observe__Session__Writer.py` | Write/read JSONL session files at `~/.sg/aws/observe/sessions/` (0600) |
| `service/Observe__Agent__Tracer.py` | Cross-source trace by session_id via `Source__Registry` |

### Schemas / collections

| File | Fields |
|------|--------|
| `schemas/Schema__Observe__Source__Status.py` | `name: Safe_Str__Observe__Source_Name`, `connected: bool`, `stream_count: int`, `last_event: Safe_Str__Observe__Event_Time` |
| `collections/List__Schema__Observe__Source__Status.py` | `items: List[Schema__Observe__Source__Status]` |

### Primitives (v0.2.30 Open-2)

| File | Description |
|------|-------------|
| `primitives/Safe_Str__Observe__Source_Name.py` | REPLACE, allow_empty — source adapter name |
| `primitives/Safe_Str__Observe__Event_Time.py` | REPLACE, allow_empty — ISO-8601 last event timestamp |

### Tests

```
tests/unit/sgraph_ai_service_playwright__cli/aws/observe/
├── _Stub__Source__Adapter.py       — in-memory fake (no mocks)
├── test_Source__Registry.py        — 6 tests
├── test_Observe__Agent__Tracer.py  — 5 tests
└── test_Cli__Observe.py            — 8 tests (19 total)
```

All 19 tests pass in CI.

### User guide

`library/docs/cli/sg-aws/16__observe.md`

---

## What does NOT exist yet

- Real `S3__AWS__Client` body (owned by Slice A)
- Real `CloudTrail__AWS__Client` body (owned by Slice F)
- Session capture hooked into CLI commands (writer exists but not wired to `tail`)
- `sg aws observe` wired into the top-level `sg aws` Typer app (pending Slice H PR merge)
