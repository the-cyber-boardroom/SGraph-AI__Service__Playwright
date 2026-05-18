---
title: "Reality — sg aws cloudtrail"
domain: cli
subdomain: aws-cloudtrail
version: v0.2.29
slice: F
status: LANDED; updated v0.2.30 Open-2 (typed primitives)
date: 2026-05-17
---

# Reality: `sg aws cloudtrail` (LANDED — v0.2.29)

## What exists

Read-only CloudTrail events and trail inspection CLI surface. Landed in v0.2.29 Slice F.

---

## Files

### CLI

| File | Class | Purpose |
|------|-------|---------|
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/cli/Cli__CloudTrail.py` | `Cli__CloudTrail` (module-level `app`) | Typer app — `events list`, `events show`, `trail list`, `trail show` |

### Service

| File | Class | Purpose |
|------|-------|---------|
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/service/CloudTrail__AWS__Client.py` | `CloudTrail__AWS__Client` | boto3 boundary — all CloudTrail API calls |

### Schemas

| File | Class | Fields |
|------|-------|--------|
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/schemas/Schema__CloudTrail__Event.py` | `Schema__CloudTrail__Event` | event_id, event_time, event_name, username, source_ip_address, aws_region, request_parameters, response_elements, resources, error_code, error_message |
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/schemas/Schema__CloudTrail__Trail.py` | `Schema__CloudTrail__Trail` | name, s3_bucket_name, home_region, is_multi_region_trail, include_global_service_events, log_file_validation_enabled, trail_arn, is_logging |

### Collections

| File | Class | Element type |
|------|-------|-------------|
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/collections/List__Schema__CloudTrail__Event.py` | `List__Schema__CloudTrail__Event` | `Schema__CloudTrail__Event` |
| `sgraph_ai_service_playwright__cli/aws/cloudtrail/collections/List__Schema__CloudTrail__Trail.py` | `List__Schema__CloudTrail__Trail` | `Schema__CloudTrail__Trail` |

### Primitives (v0.2.30 Open-2)

| File | Description |
|------|-------------|
| `primitives/Safe_Str__CloudTrail__Trail_Name.py` | REPLACE, allow_empty — trail name |
| `primitives/Safe_Str__CloudTrail__Event_Id.py` | REPLACE, allow_empty — event UUID |
| `primitives/Safe_Str__CloudTrail__Event_Time.py` | REPLACE, allow_empty — ISO-8601 timestamp |
| `primitives/Safe_Str__CloudTrail__Event_Name.py` | REPLACE, allow_empty — API action name |
| `primitives/Safe_Str__CloudTrail__Username.py` | REPLACE, allow_empty — IAM user/role name |
| `primitives/Safe_Str__CloudTrail__IP_Address.py` | REPLACE, allow_empty — source IP |
| `primitives/Safe_Str__CloudTrail__Error_Code.py` | REPLACE, allow_empty — AWS error code |
| `primitives/Safe_Str__CloudTrail__Error_Message.py` | REPLACE, allow_empty — free-form error text |
| `primitives/Safe_Str__CloudTrail__Json_Blob.py` | REPLACE, allow_empty — JSON-serialised AWS data |

All previously raw `str` fields in `Schema__CloudTrail__Event` now use typed primitives.
`aws_region → Safe_Str__AWS__Region`; `request_parameters`, `response_elements`, `resources → Safe_Str__CloudTrail__Json_Blob`.
`Schema__CloudTrail__Trail`: `s3_bucket_name → Safe_Str__S3__Bucket`, `home_region → Safe_Str__AWS__Region`, `trail_arn → Safe_Str__AWS__ARN`.

### Tests

| File | Class | Count |
|------|-------|-------|
| `tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/service/CloudTrail__AWS__Client__In_Memory.py` | `CloudTrail__AWS__Client__In_Memory` | fake |
| `tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/service/test_CloudTrail__AWS__Client.py` | `Test__CloudTrail__AWS__Client` | 15 tests |
| `tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/cli/test_Cli__CloudTrail.py` | `Test__Cli__CloudTrail__Events`, `Test__Cli__CloudTrail__Trail` | 11 tests |

---

## Commands

| Command | Flags | Notes |
|---------|-------|-------|
| `sg aws cloudtrail events list` | `--user`, `--service`, `--action`, `--since` (1h), `--limit` (100), `--json` | CloudTrail supports one LookupAttribute at a time; priority: action > user > service |
| `sg aws cloudtrail events show <event_id>` | `--json` | Searches last 24h; exit 1 if not found |
| `sg aws cloudtrail trail list` | `--json` | Lists all trails including `is_logging` status |
| `sg aws cloudtrail trail show <name>` | `--json` | Full trail config + logging status; exit 1 if not found |

---

## Design decisions

- **Read-only** — no mutation gate; all commands query CloudTrail data only.
- **Single LookupAttribute** — AWS CloudTrail API restriction; filter priority documented in CLI help.
- **boto3 seam** — `CloudTrail__AWS__Client.client()` is the single boto3 injection point; tests override via `CloudTrail__AWS__Client__In_Memory`.
- **Since parser built-in** — relative (`1h`, `30m`) and absolute ISO UTC expressions parsed inside the service layer; no separate parser class needed at this scale.
- **Stub replaced** — the foundation stub at `service/CloudTrail__AWS__Client.py` (which raised `NotImplementedError`) was replaced in place by the real implementation.

---

## Docs

- User guide: `library/docs/cli/sg-aws/13__cloudtrail.md`
- README row updated: `library/docs/cli/sg-aws/README.md` row 14

---

## What does NOT exist

- Mutations (none planned for CloudTrail in this slice).
- `sg aws cloudtrail events filter` with multiple simultaneous attributes (AWS API restriction).
- `sg aws observe` CloudTrail source adapter (Slice H — PROPOSED).
