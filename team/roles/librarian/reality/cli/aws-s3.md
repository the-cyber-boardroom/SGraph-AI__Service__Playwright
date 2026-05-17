---
title: "Reality — sg aws s3 (CLI surface)"
file: aws-s3.md
domain: cli
status: LANDED — v0.2.29
landed_commit: TBD — backfill after merge
date: 2026-05-17
author: Dev (Claude)
---

# Reality: `sg aws s3`

**Status: LANDED — v0.2.29**

The `sg aws s3` command surface is implemented and unit-tested on branch
`claude/aws-primitives-support-uNnZY`.

---

## What exists

### Production files

```
sgraph_ai_service_playwright__cli/aws/s3/
├── cli/
│   └── Cli__S3.py                      # full Typer CLI for all 16 commands
├── service/
│   ├── S3__AWS__Client.py              # boto3 boundary (EXCEPTION comment)
│   ├── S3__Source__Adapter.py          # implements Source__Contract
│   ├── S3__Format__Detector.py         # format detection (ext + sniff)
│   └── S3__Vim__Editor.py              # vim round-trip edit flow
├── schemas/
│   ├── Schema__S3__Object.py           # (pre-existing from Foundation)
│   ├── Schema__S3__Bucket.py
│   ├── Schema__S3__List__Response.py
│   └── Schema__S3__Stat.py
├── primitives/
│   ├── Safe_Str__S3__URI.py            # (pre-existing from Foundation)
│   ├── Safe_Str__S3__Bucket.py         # (pre-existing from Foundation)
│   ├── Safe_Str__S3__Key.py            # (pre-existing from Foundation)
│   └── Safe_Str__S3__ETag.py          # (pre-existing from Foundation)
├── enums/
│   ├── Enum__S3__Storage__Class.py     # (pre-existing from Foundation)
│   └── Enum__S3__Object__Format.py
└── collections/
    ├── List__Schema__S3__Object.py
    └── List__Schema__S3__Bucket.py
```

### Test files

```
tests/unit/sgraph_ai_service_playwright__cli/aws/s3/
└── service/
    ├── S3__AWS__Client__In_Memory.py       # in-memory fake S3 boto3 client
    ├── test_S3__AWS__Client.py             # 26 tests
    ├── test_S3__Source__Adapter.py         # 10 tests
    └── test_S3__Mutation__Gate.py          # 4 tests
```

Total: **40 unit tests** — all pass.

---

## Commands implemented

| Command | Tier | Status |
|---------|------|--------|
| `ls [path]` | read-only | LANDED |
| `view <path>` | read-only | LANDED |
| `cat <path>` | read-only | LANDED |
| `head <path>` | read-only | LANDED |
| `tail <path>` | read-only | LANDED |
| `stat <path>` | read-only | LANDED |
| `presign <path>` | read-only | LANDED |
| `search <path> --pattern P` | read-only | LANDED |
| `cp <src> <dst>` | mutating | LANDED |
| `mv <src> <dst>` | mutating | LANDED |
| `rm <path>` | mutating | LANDED |
| `sync <local> <s3-path>` | mutating | LANDED |
| `edit <path>` | mutating | LANDED |
| `bucket-list` | read-only | LANDED |
| `bucket-stat <bucket>` | read-only | LANDED |
| `bucket-create <bucket>` | mutating | LANDED |

**Mutation gate:** `SG_AWS__S3__ALLOW_MUTATIONS=1`

---

## Out of scope for this slice

- `bucket-config` — set versioning/lifecycle/encryption (deferred to v0.2.30)
- Vault-aware `s3 vault-open/sync/diff/ls` commands (deferred to v0.2.30)
- Migration of existing `elastic/lets/cf` direct boto3 S3 callers — deferred; explicit v0.2.30 follow-up

---

## Key design decisions

- `S3__AWS__Client` uses boto3 directly (EXCEPTION pattern): osbot_aws S3 support
  was not available in the installed version at time of implementation.
- `S3__Source__Adapter` implements `Source__Contract` from `aws/_shared/` so Slice H
  (observability) can consume S3 without depending on this slice's internals.
- The vim round-trip (`S3__Vim__Editor`) uses `IfMatch` conditional PUT for ETag
  conflict detection; conflict files saved as `<tmpfile>.conflict` with exit 1.
- `bucket-create` defaults: public access fully blocked, versioning enabled.
- `sync` is local→S3 only in v0.2.29; S3→local and S3→S3 sync deferred.

---

## Docs

User guide: `library/docs/cli/sg-aws/09__s3.md`
