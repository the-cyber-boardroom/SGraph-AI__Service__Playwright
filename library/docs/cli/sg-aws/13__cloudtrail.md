---
title: "sg aws cloudtrail — User Guide"
file: 13__cloudtrail.md
author: Dev (Claude)
date: 2026-05-17
version: v0.2.29
slice: F
status: LANDED
---

# `sg aws cloudtrail` — CloudTrail Events and Trail Inspection

Read-only inspection of AWS CloudTrail events and trail configuration. No mutation gate required.

---

## Command tree

```
sg aws cloudtrail
├── events
│   ├── list   [--user] [--service] [--action] [--since] [--limit] [--json]
│   └── show   <event_id>  [--json]
└── trail
    ├── list   [--json]
    └── show   <name>  [--json]
```

---

## `events list`

Fetch recent CloudTrail events with optional filters.

```bash
# Default: last 1 hour, up to 100 events
sg aws cloudtrail events list

# Filter by IAM username
sg aws cloudtrail events list --user alice

# Filter by event name (API action)
sg aws cloudtrail events list --action PutObject

# Filter by event source (AWS service endpoint)
sg aws cloudtrail events list --service s3.amazonaws.com

# Change time window (last 30 minutes)
sg aws cloudtrail events list --since 30m

# JSON output, last 6 hours, up to 200 events
sg aws cloudtrail events list --since 6h --limit 200 --json
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--user` | `` | IAM username to filter by |
| `--service` | `` | Event source endpoint (e.g. `s3.amazonaws.com`) |
| `--action` | `` | Event name / API action (e.g. `PutObject`) |
| `--since` | `1h` | Time window: `30s`, `5m`, `2h`, `1d`, or ISO UTC |
| `--limit` | `100` | Maximum events returned |
| `--json` | false | Machine-readable output |

> **Note:** CloudTrail `LookupEvents` supports only one filter attribute at a time. If multiple of `--user`, `--service`, `--action` are given, priority is: `--action` > `--user` > `--service`.

### `--since` time expressions

| Expression | Meaning |
|------------|---------|
| `30s` | 30 seconds ago |
| `5m` | 5 minutes ago |
| `2h` | 2 hours ago |
| `1d` | 1 day ago |
| `2026-05-17T12:00:00Z` | Absolute UTC timestamp |

---

## `events show`

Show full details of a single CloudTrail event by its EventId (UUID).

```bash
sg aws cloudtrail events show a1b2c3d4-e5f6-7890-abcd-ef1234567890
sg aws cloudtrail events show a1b2c3d4-e5f6-7890-abcd-ef1234567890 --json
```

The event is searched in the last 24 hours of CloudTrail history. Returns exit code 1 if not found.

---

## `trail list`

List all CloudTrail trails in the current AWS account.

```bash
sg aws cloudtrail trail list
sg aws cloudtrail trail list --json
```

Output columns: Name, Home Region, S3 Bucket, Multi-Region, Global Events, Logging.

---

## `trail show`

Show full configuration of a single trail by name or ARN.

```bash
sg aws cloudtrail trail show my-prod-trail
sg aws cloudtrail trail show my-prod-trail --json
```

Returns exit code 1 if the trail is not found.

---

## JSON output shape

### `events list`

```json
[
  {
    "event_id":          "a1b2c3d4-...",
    "event_time":        "2026-05-17 12:34:56+00:00",
    "event_name":        "PutObject",
    "username":          "alice",
    "source_ip_address": "1.2.3.4",
    "aws_region":        "us-east-1",
    "error_code":        "",
    "error_message":     ""
  }
]
```

### `events show`

All fields from `events list` plus `request_parameters`, `response_elements`, and `resources` (each a JSON string).

### `trail list` / `trail show`

```json
[
  {
    "name":                          "my-prod-trail",
    "s3_bucket_name":                "my-logs-bucket",
    "home_region":                   "us-east-1",
    "is_multi_region_trail":         true,
    "include_global_service_events": true,
    "log_file_validation_enabled":   true,
    "trail_arn":                     "arn:aws:cloudtrail:us-east-1:123:trail/my-prod-trail",
    "is_logging":                    true
  }
]
```

---

## AWS credentials and region

All commands use the standard AWS credential chain. CloudTrail is regional — override with `AWS_REGION=eu-west-1` as needed.

```bash
AWS_REGION=eu-west-1 sg aws cloudtrail events list --since 2h --json
```

---

## Backing classes

| Layer | Class | Path |
|-------|-------|------|
| CLI | `Cli__CloudTrail` | `sgraph_ai_service_playwright__cli/aws/cloudtrail/cli/` |
| Service | `CloudTrail__AWS__Client` | `sgraph_ai_service_playwright__cli/aws/cloudtrail/service/` |
| Schemas | `Schema__CloudTrail__Event`, `Schema__CloudTrail__Trail` | `sgraph_ai_service_playwright__cli/aws/cloudtrail/schemas/` |
| Collections | `List__Schema__CloudTrail__Event`, `List__Schema__CloudTrail__Trail` | `sgraph_ai_service_playwright__cli/aws/cloudtrail/collections/` |
