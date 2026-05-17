---
title: "CLI — sg aws iam graph (v0.2.29 Slice D)"
file: aws-iam-graph.md
domain: cli
author: Dev (Claude)
date: 2026-05-17
status: EXISTS — implemented in feat(v0.2.29) Slice D commit on claude/aws-primitives-support-uNnZY
appsec_note: HIGH BLAST-RADIUS — delete verb. AppSec sign-off required before merging to dev.
---

# EXISTS — `sg aws iam graph`

IAM-as-graph sub-command tree under `sg aws iam`. Provides discovery, snapshot management, filtering, transitive-permission walk, and bulk-delete with mandatory dry-run gate.

**AppSec: HIGH BLAST-RADIUS.** The `delete` verb can remove multiple IAM roles in a single pass. Three enforced layers:
1. `SG_AWS__IAM__ALLOW_MUTATIONS=1` env-var gate (shared with `iam role/policy` mutations)
2. Dry-run by default — no AWS API calls unless `--confirm` is passed
3. `--confirm` flag explicitly required for real deletion

---

## Verbs

| Verb | Tier | Notes |
|------|------|-------|
| `discover [--json]` | read-only | Pulls IAM state; writes snapshot to `~/.sg/aws/iam-graph/<id>/` |
| `show [--snapshot] [--json]` | read-only | Metadata for a snapshot (counts, timestamps) |
| `walk ROOT [--depth] [--json]` | read-only | BFS from root node following managed/inline policy edges |
| `filter --unused [--days]` | read-only | Roles with no recent activity |
| `filter --pattern GLOB` | read-only | Name glob (fnmatch) |
| `filter --aws-default` | read-only | AWS-auto-created and service-linked roles |
| `filter --output FILE` | read-only | Write candidate JSON for `delete --from` |
| `delete --from FILE [--confirm] [--yes]` | **mutating** | Dry-run by default; `--confirm` + mutation gate required to mutate |
| `stats [--snapshot] [--json]` | read-only | Scope-breadth histogram |
| `snapshots list [--json]` | read-only | All local snapshots |
| `snapshots diff A B [--json]` | read-only | Structural diff of two snapshots |

---

## Production files

| Path | Class | Notes |
|------|-------|-------|
| `aws/iam/graph/cli/Cli__Iam__Graph.py` | — | Typer app; wired into `Cli__Iam.py` via `iam_app.add_typer` |
| `aws/iam/graph/service/Iam__Discovery__Orchestrator.py` | `Iam__Discovery__Orchestrator` | Existing class (Foundation); reuses `IAM__AWS__Client` |
| `aws/iam/graph/service/Iam__Graph__Builder.py` | `Iam__Graph__Builder` | Converts node lists → serialisable dicts + snapshot meta |
| `aws/iam/graph/service/Iam__Graph__Filter.py` | `Iam__Graph__Filter` | unused / pattern / aws-default predicates |
| `aws/iam/graph/service/Iam__Graph__Vault__Writer.py` | `Iam__Graph__Vault__Writer` | Reads/writes `~/.sg/aws/iam-graph/`; 0700 dirs, 0600 files |
| `aws/iam/graph/service/Iam__Graph__Snapshot__Diff.py` | `Iam__Graph__Snapshot__Diff` | Structural diff of two snapshot directories |
| `aws/iam/graph/service/Iam__Graph__Walker.py` | `Iam__Graph__Walker` | BFS transitive walk |
| `aws/iam/graph/service/Iam__Graph__Cleanup.py` | `Iam__Graph__Cleanup` | Build plan + execute; service-linked roles always skipped |

Schemas, enums, primitives, and collections are under `aws/iam/graph/{schemas,enums,primitives,collections}/`. All created by Foundation PR (Slice D prep).

---

## Snapshot format

```
~/.sg/aws/iam-graph/<ISO-ts-Z>__<6-char-nonce>/
├── snapshot.json      # Schema__IAM__Graph__Snapshot
├── roles/<name>.json  # Schema__IAM__Graph__Node per role
├── policies/<name>.json
├── users/<name>.json
├── groups/<name>.json
└── edges.json         # list of Schema__IAM__Graph__Edge dicts
```

---

## Tests

| Path | Coverage |
|------|----------|
| `tests/unit/.../graph/service/test_Iam__Discovery__Orchestrator.py` | discover_nodes + edges, aws-default flag |
| `tests/unit/.../graph/service/test_Iam__Graph__Filter.py` | unused / pattern / aws-default predicates |
| `tests/unit/.../graph/service/test_Iam__Graph__Cleanup.py` | dry-run gate, service-linked skip, real delete |
| `tests/unit/.../graph/service/test_Iam__Graph__Snapshot__Diff.py` | identical / added / removed / empty diffs |
| `tests/unit/.../graph/cli/test_Cli__Iam__Graph.py` | CLI: discover, show, filter, delete gate, snapshots list |

32 unit tests, all passing.

---

## Security controls

- Service-linked roles are always excluded from delete candidates (IAM API cannot delete them directly)
- `delete` without `--confirm` is a no-op dry-run, even with `SG_AWS__IAM__ALLOW_MUTATIONS=1`
- No AWS credentials stored; all calls use the standard credential chain
- Snapshot files: directory 0700, files 0600

---

## See also

- User guide: `library/docs/cli/sg-aws/12__iam-graph.md`
- Upstream IAM surface: `aws-iam.md` (this directory) — `role`, `policy` verbs
- Dev pack spec: `library/dev_packs/v0.2.29__sg-aws-iam-graph/README.md`
