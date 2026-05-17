---
title: "sg aws iam graph — IAM-as-graph discovery and cleanup"
file: 12__iam-graph.md
author: Dev (Claude)
date: 2026-05-17
parent: README.md
appsec: HIGH BLAST-RADIUS — delete verb requires SG_AWS__IAM__ALLOW_MUTATIONS=1 AND --confirm
---

# 12 — `sg aws iam graph`

IAM-as-graph: discover all IAM roles into a local snapshot, filter by unused / pattern / AWS-default, walk transitive permissions, and bulk-delete with a mandatory dry-run gate.

**Mutation gate:** `SG_AWS__IAM__ALLOW_MUTATIONS=1` (same gate as `sg aws iam role/policy`).
**Additional safety gate for delete:** `--confirm` flag is required even when the mutation gate is set.

Subcommand groups:

| Group | What it does |
|-------|--------------|
| `discover` | Pull current IAM state into a local snapshot |
| `show` | Summary of a snapshot (counts by node type) |
| `walk` | Transitive permission walk from a role/user/policy node |
| `filter` | Subset nodes by unused / name-pattern / aws-default |
| `delete` | Dry-run or real bulk-delete from a candidate file |
| `stats` | Scope-breadth histogram (wildcard vs specific) |
| `snapshots list` | List all local snapshots |
| `snapshots diff` | Diff two snapshots |

---

## AppSec note — HIGH BLAST-RADIUS

`sg aws iam graph delete` can delete multiple IAM roles in a single pass. Three layers of safety are enforced:

1. **Mutation gate** — `SG_AWS__IAM__ALLOW_MUTATIONS=1` must be set in the shell.
2. **Dry-run by default** — omitting `--confirm` always produces a dry-run plan with no AWS API calls.
3. **Confirm flag** — `--confirm` triggers real deletion. Combine with `--yes` to skip the `[y/N]` prompt.

Service-linked roles are always skipped — the IAM API cannot delete them via the standard role delete path. They appear in `show` with an `is_service_linked=true` tag.

Never run `sg aws iam graph delete --from <file> --confirm` in a CI pipeline without first reviewing the candidate file output from `sg aws iam graph filter ... --output <file>`.

---

## Snapshot storage

Snapshots are stored in `~/.sg/aws/iam-graph/` on the local filesystem.

```
~/.sg/aws/iam-graph/<snapshot-id>/
├── snapshot.json              # top-level metadata
├── roles/<role-name>.json     # one file per role
├── policies/<name>.json       # one file per managed-policy node
├── users/<name>.json
├── groups/<name>.json
└── edges.json                 # all attachment + trust edges
```

Snapshot ID format: `<ISO-timestamp-Z>__<6-char-nonce>` — e.g. `2026-05-17T12:34:56Z__a1b2c3`.

Directory permissions: 0700. File permissions: 0600.

---

## `discover`

Pull the current IAM state and write a fresh snapshot.

```bash
sg aws iam graph discover
sg aws iam graph discover --json
```

Output JSON keys: `snapshot_id`, `captured_at`, `role_count`, `edge_count`, `path`.

---

## `show [--snapshot ID]`

Show metadata for a snapshot. Defaults to the most recent one.

```bash
sg aws iam graph show
sg aws iam graph show --snapshot 2026-05-17T12:34:56Z__a1b2c3
sg aws iam graph show --json
```

Displayed fields: `snapshot_id`, `captured_at`, `roles`, `policies`, `users`, `groups`, `edges`, `account`, `region`.

---

## `walk ROOT [--depth N]`

Transitive permission walk starting from a role ARN or role name. Follows `managed_policy` and `inline_policy` edges up to `--depth` hops (default 3).

```bash
sg aws iam graph walk arn:aws:iam::123456789012:role/sg-vault-publish --depth 3
sg aws iam graph walk sg-vault-publish --json
```

Output JSON keys: `root`, `max_depth`, `node_count`, `nodes` (each node includes `walk_depth`).

---

## `filter`

Produce a candidate list. The three modes are mutually exclusive per invocation:

### `--unused [--days N]`

Roles with no `last_used` timestamp, or whose `last_used` is older than `--days` (default 90).

```bash
sg aws iam graph filter --unused
sg aws iam graph filter --unused --days 180 --output /tmp/stale.json
```

### `--pattern GLOB`

Filter by name glob (Python `fnmatch` semantics).

```bash
sg aws iam graph filter --pattern "sg-*" --json
sg aws iam graph filter --pattern "AWSServiceRole*" --output /tmp/aws-svc.json
```

### `--aws-default`

Roles with `is_aws_default=true` or `is_service_linked=true`.

```bash
sg aws iam graph filter --aws-default --json
```

**Common flags:** `--output/-o FILE`, `--snapshot ID`, `--json`.

The `--output` file is the input for `delete --from`.

---

## `delete --from FILE`  ⚠ mutates

Delete roles listed in a candidate JSON file (output of `filter --output`).

**Dry-run by default.** No API calls unless `--confirm` is also passed.

```bash
# Dry-run (safe — always does this by default)
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/stale.json

# Real deletion
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/stale.json --confirm --yes
```

**Flags:**
- `--from FILE` (required) — candidate JSON file
- `--confirm` — actually delete (omit for dry-run)
- `--yes/-y` — skip confirmation prompt
- `--json` — machine-readable output

Output JSON keys (with `--json`): `dry_run`, `candidate_count`, `deleted_count`, `error_count`, `executed`.

**Recommended workflow:**

```bash
# 1. Discover
sg aws iam graph discover

# 2. Build candidate list
sg aws iam graph filter --unused --days 90 --output /tmp/stale.json

# 3. Review the candidate list
cat /tmp/stale.json | jq '.candidates[].name'

# 4. Dry-run (default)
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/stale.json --json

# 5. Real deletion (after review)
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/stale.json --confirm --yes

# 6. Re-discover and diff
sg aws iam graph discover
sg aws iam graph snapshots diff <before-id> <after-id> --json
```

---

## `stats [--snapshot ID]`

Scope-breadth histogram for all nodes in a snapshot.

```bash
sg aws iam graph stats
sg aws iam graph stats --snapshot 2026-05-17T12:34:56Z__a1b2c3 --json
```

Output JSON keys: `snapshot_id`, `total`, `by_scope_breadth` (map of `wildcard`/`prefix_scoped`/`specific` → count).

---

## `snapshots list`

List all snapshots in `~/.sg/aws/iam-graph/`, newest first.

```bash
sg aws iam graph snapshots list
sg aws iam graph snapshots list --json
```

---

## `snapshots diff A B`

Structural diff between two snapshot IDs.

```bash
sg aws iam graph snapshots diff 2026-05-17T10:00:00Z__aaaaaa 2026-05-17T11:00:00Z__bbbbbb
sg aws iam graph snapshots diff <before> <after> --json | jq '.removed | length'
```

Output JSON keys: `snapshot_a`, `snapshot_b`, `added_nodes`, `removed_nodes`, `added_edges`, `removed_edges`, `node_delta`, `edge_delta`.

---

## What backs this

Code at `sgraph_ai_service_playwright__cli/aws/iam/graph/`:

| Class | What it does |
|-------|-------------|
| `Iam__Discovery__Orchestrator` | Pulls IAM state via `IAM__AWS__Client` (roles + edges) |
| `Iam__Graph__Builder` | Converts node lists to serialisable dicts + snapshot metadata |
| `Iam__Graph__Filter` | `unused` / `pattern` / `aws-default` predicates |
| `Iam__Graph__Vault__Writer` | Writes/reads snapshots to/from `~/.sg/aws/iam-graph/` |
| `Iam__Graph__Snapshot__Diff` | Diffs two snapshots by node_id key |
| `Iam__Graph__Cleanup` | Builds and executes cleanup plans; service-linked roles always skipped |
| `Iam__Graph__Walker` | BFS transitive walk from a root node |

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/iam/graph/`.
