---
title: "Reality — sg aws logs"
file: aws-logs.md
domain: cli
author: Librarian (Claude)
date: 2026-05-19
status: CURRENT — shipped in v0.2.33 (Slice 0c)
parent: cli/index.md
---

# Reality — `sg aws logs`

## Status

CURRENT. Implemented in v0.2.33 Slice 0c on branch `claude/review-vault-publish-spec-FT9hq`.

## What exists

### Production files

```
sgraph_ai_service_playwright__cli/aws/logs/
├── cli/
│   └── Cli__Logs.py                — Typer app with groups/group/tail sub-trees
├── service/
│   ├── Logs__AWS__Client.py        — boto3 CloudWatch Logs boundary (EXCEPTION noted in header)
│   ├── Logs__Insights__Queries.py  — CloudWatch Logs Insights query helpers
│   └── Logs__Time__Parser.py       — human-readable duration → start_time_ms (e.g. "30m", "1h")
├── schemas/
│   ├── Schema__Logs__Group.py          — name, arn, retention_days, stored_bytes
│   ├── Schema__Logs__Event.py          — timestamp, message, stream
│   ├── Schema__Logs__Events__Response.py
│   ├── Schema__Logs__Query__Result.py
│   └── Schema__Logs__Query__Row.py
└── primitives/
    ├── Safe_Str__Log__Group.py     — log group name (printable ASCII)
    └── Safe_Str__Log__Stream.py    — log stream name (printable ASCII)
```

### Commands

| Verb | Tier |
|------|------|
| `groups list [--prefix P] [--json]` | read-only |
| `group describe <name> [--json]` | read-only |
| `group create <name> [--retention 7] [--yes]` | mutating — gated by `SG_AWS__LOGS__ALLOW_MUTATIONS=1` |
| `group delete <name> [--yes]` | mutating — gated |
| `tail <group> [--stream <prefix>] [--since 60] [--follow]` | read-only — polls CloudWatch events |

### Mutation gate

`SG_AWS__LOGS__ALLOW_MUTATIONS=1`

`group create` is idempotent: if the group already exists, the command prints
"Already exists (skipped)" and exits 0.

### Default retention

`group create --retention 7` (days). Pass `--retention 0` for no expiry policy.

### Tests

```
tests/unit/sgraph_ai_service_playwright__cli/aws/logs/
├── service/
│   └── test_Logs__Time__Parser.py   — duration string parsing
```

Total: 66 unit tests in the logs sub-package.

## What does NOT exist

- Integration tests (`tests/integration/…/logs/`) — gated on live AWS credentials
- `logs insights` sub-command — `Logs__Insights__Queries` is a service class but no CLI verb wraps it yet
- Log stream listing (`streams list` / `stream describe`) — not needed for the vault-app fargate use case in v1

## Decisions

- boto3 used directly (EXCEPTION pattern) — no osbot-aws CloudWatch Logs wrapper at the time of writing
- `tail` uses `filter_log_events` (not `get_log_events`) so it can filter across streams by prefix
- `--since` unit is minutes (default 60) for consistency with the existing `task logs --since 30m` flag
- `Logs__AWS__Client` is also consumed by `Vault_App__Fargate__Setup._phase_logs` for log group create/delete during setup

## See also

- Parent: [`cli/index.md`](index.md)
- Related: [`aws-fargate.md`](aws-fargate.md) — `task logs` verb uses `Logs__AWS__Client`
- Related: [`sg-compute/index.md`](../sg-compute/index.md) — vault-app fargate setup uses `Logs__AWS__Client`
