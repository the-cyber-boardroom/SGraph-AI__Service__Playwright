---
title: "v0.2.29 — sg aws cloudtrail (Slice F)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: S — ~700 prod lines, ~400 test lines, ~1.5 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_briefs:
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__unified-observability-session.md
feature_branch: claude/aws-primitives-support-uNnZY-cloudtrail
---

# `sg aws cloudtrail` — Slice F

Read-only CloudTrail surface. Provides the events + trails primitives that Slice D Phase 4 (IAM-graph evidence layer — v0.2.30) and Slice H (observability v1) build on.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/aws-and-infrastructure/` before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone — the smallest. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

Consumer: Slice H (observability v1) uses `CloudTrail__AWS__Client` as one of its three sources. Slice H builds against the Foundation-shipped interface stub in parallel with this slice; the real client lands as part of this PR.

---

## Source briefs

CloudTrail isn't given its own brief — it's a primitive demanded by two consumer briefs:

- [`v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md) — Phase 4 evidence layer reads CloudTrail per-role activity (consumed in v0.2.30)
- [`v0.27.43__arch-brief__unified-observability-session.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__unified-observability-session.md) — CloudTrail is one of three v1 sources

This slice ships the primitive layer only; the consumers wire it in.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/cloudtrail/` (Foundation ships the skeleton; you fill in the bodies)

### Verbs

| Verb | Tier | Notes |
|------|------|-------|
| `events list` | read-only | Per-event filters: `--user X`, `--service X`, `--action X`, `--resource arn:...`, `--since <duration>`, `--until <ts>`, `--region`, `--json`, `--limit N` |
| `events show <event-id>` | read-only | Full event JSON |
| `trail list` | read-only | All trails in the account |
| `trail show <trail-name>` | read-only | Trail config: S3 destination, multi-region, log-validation, KMS, event selectors |

**No mutation gate.** This is a read-only surface.

### Source-contract adapter

Implements `Source__Contract` from `aws/_shared/source_contract/` so Slice H can consume CloudTrail uniformly:

```python
class CloudTrail__Source__Adapter(Source__Contract):
    def connect(self) -> bool: ...
    def list_streams(self) -> List__Schema__Source__Stream__Ref: ...   # returns: trail names
    def tail(self, stream, since) -> Source__Stream: ...                 # streams events from a trail's S3 destination
    def query(self, q) -> Source__Result__Page: ...                      # uses CloudTrail Lookup Events API for last 90d
    def stats(self, stream, agg) -> Schema__Source__Stats: ...
    def schema(self, stream) -> Schema__Source__Stream__Schema: ...
```

The Lookup Events API is rate-limited (2 TPS) — `CloudTrail__AWS__Client` rate-limits internally with a token bucket.

---

## Production files (indicative)

```
aws/cloudtrail/
├── cli/
│   ├── Cli__CloudTrail.py
│   └── verbs/
│       ├── Verb__CloudTrail__Events__List.py
│       ├── Verb__CloudTrail__Events__Show.py
│       ├── Verb__CloudTrail__Trail__List.py
│       └── Verb__CloudTrail__Trail__Show.py
├── service/
│   ├── CloudTrail__AWS__Client.py          # wraps Sg__Aws__Session
│   ├── CloudTrail__Rate__Limiter.py        # 2 TPS token bucket
│   ├── CloudTrail__Source__Adapter.py      # Source__Contract impl
│   └── CloudTrail__S3__Reader.py           # reads trail logs from their S3 destination (for tail beyond 90d)
├── schemas/                                # Schema__CloudTrail__Event, ...Trail__Config, ...Event__Selector, etc.
├── enums/                                  # Enum__CloudTrail__Event__Source, Enum__CloudTrail__Event__Category
├── primitives/                             # Safe_Str__CloudTrail__Event_Id, Safe_Str__CloudTrail__Trail_Arn
└── collections/                            # List__Schema__CloudTrail__Event
```

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned)
- The IAM-graph Phase 4 evidence layer — v0.2.30 pack
- The observability REPL — Slice H

---

## Acceptance

```bash
# events
sg aws cloudtrail events list --since 1h
sg aws cloudtrail events list --user my-iam-user --since 24h --json | jq length
sg aws cloudtrail events list --service iam --action CreateRole --since 7d
sg aws cloudtrail events list --resource arn:aws:s3:::sg-test-bucket --since 7d
sg aws cloudtrail events show <event-id>

# trails
sg aws cloudtrail trail list --json | jq '.[].name'
sg aws cloudtrail trail show <trail-name>

# Source contract via Slice H once integrated:
sg aws observe                                                          # enter REPL
> sources                                                                # cloudtrail visible
> tail --source cloudtrail --stream <trail-name> --since 1h
> query --source cloudtrail "user:my-iam-user since:24h"

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/ -v
SG_AWS__CLOUDTRAIL__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/cloudtrail/ -v
```

---

## Deliverables

1. All files under `aws/cloudtrail/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/cloudtrail/`
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/cloudtrail/` (gated)
4. New user-guide page `library/docs/cli/sg-aws/14__cloudtrail.md` (~4 KB; small surface)
5. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
6. Reality-doc update: new `team/roles/librarian/reality/aws-and-infrastructure/cloudtrail.md`

---

## Risks to watch

- **Lookup Events API limits.** 2 TPS; 90-day lookback. `events list` beyond 90 days falls back to reading the trail's S3 destination (`CloudTrail__S3__Reader`). Be explicit in the help text about which path runs.
- **Trail destination access.** Reading from S3 needs `s3:GetObject` on the trail bucket. Surface a clear error if the caller lacks it.
- **Event volume.** A busy account can return thousands of events per query. Default `--limit 100`; paginate transparently for `--json` callers up to a per-call cap.
- **Region scoping.** CloudTrail is region-scoped for management events but can be multi-region. `events list` defaults to current region + the home region of any multi-region trail. `--all-regions` enumerates every region (slow).

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-cloudtrail`

Commit message: `feat(v0.2.29): sg aws cloudtrail — events + trails read-only primitives + Source__Contract adapter`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

Independent. The smallest slice; lowest risk. Cancelling defers both the v0.2.30 IAM-graph Phase 4 evidence layer and degrades Slice H's observability to two sources (S3 + CloudWatch); neither blocks the other v0.2.29 slices.
