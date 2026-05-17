---
title: "v0.2.29 — sg aws iam graph (Slice D)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: L — ~1800 prod lines, ~700 test lines, ~3 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_brief: team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md
feature_branch: claude/aws-primitives-support-uNnZY-iam-graph
---

# `sg aws iam graph` — Slice D

The IAM-as-graph treatment: discover all roles/policies/trust relationships into a vault-stored graph snapshot, then provide CLI filters and a bulk-delete workflow for cleanup. **Phase 1 + Phase 3 only** per the source brief — evidence-driven recommendations (Phase 4) and lockdown rollout (Phases 5-6) defer to v0.2.30.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/aws-and-infrastructure/iam.md` before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

Independent of all other v0.2.29 slices in implementation. The v0.2.30 IAM-graph-Phase-4 pack depends on Slice F (CloudTrail) — out of scope here.

This is a **new sub-tree under the existing `sg aws iam` namespace**, not a new top-level group.

---

## Source brief

[`v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__iam-graph-visualisation-and-lockdown.md) is ground truth.

The brief defines six phases. This slice ships:

- **Phase 1** — IAM discovery pass with structured vault representation
- **Phase 3** — Cleanup workflow with dry-run + confirm

Explicitly deferred to v0.2.30:

- Phase 2 (graph visualisation in SG/App) — depends on a UI surface that doesn't belong in the CLI pack
- Phase 4 (CloudTrail-evidence recommendations) — depends on Slice F's CloudTrail primitives
- Phase 5 (expansion workflow) — depends on Slice G's scope catalogue being stable
- Phase 6 (SG command lockdown) — depends on Phase 5

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/iam/graph/` (new sub-folder of existing `aws/iam/`; Foundation ships the skeleton)

### Verbs (`sg aws iam graph ...`)

| Verb | Tier | Notes |
|------|------|-------|
| `discover` | read-only | Pull current IAM state into a snapshot; writes to a vault location |
| `show [--snapshot <id>]` | read-only | Summary of a snapshot (counts by node type, recency, AWS-default vs user-created) |
| `walk <root-node> [--depth N]` | read-only | Transitive permission walk from a role/user/policy node |
| `filter --unused [--days N] [--no-cloudtrail-days N]` | read-only | Filter roles by "no edges in / no recent activity" |
| `filter --pattern <glob>` | read-only | Filter by name pattern |
| `filter --aws-default` | read-only | Just the AWS-auto-created roles |
| `filter --output <file>` | read-only | Write the filtered candidate set to a file (input for `delete`) |
| `delete --from <candidate-file>` | mutating | Dry-run by default; `--confirm` actually deletes |
| `stats [--snapshot <id>]` | read-only | Counts: roles by scope-breadth (`*:*` vs prefix-scoped vs specific) |
| `snapshots list` | read-only | All snapshots in the vault |
| `snapshots diff <a> <b>` | read-only | Diff two snapshots (what changed) |

**Mutation gate:** `SG_AWS__IAM__ALLOW_MUTATIONS=1` (existing — already covers `iam role/policy create/delete/attach/detach`). `graph delete` honours the same gate; the `--confirm` flag is additionally required to actually mutate.

### Snapshot format (vault layout)

```
<vault-root>/aws/iam-graph/<snapshot-id>/
├── snapshot.json                # Schema__IAM__Graph__Snapshot — top-level metadata
├── roles/<role-name>.json        # one file per role
├── policies/<policy-name>.json   # one file per managed policy
├── users/<user-name>.json
├── groups/<group-name>.json
└── edges.json                   # all attachment + trust + assume-role edges
```

Snapshot ID format: `<ISO-timestamp-Z>__<6-char-nonce>`. Stored to the vault via the standard vault writer.

---

## Production files (indicative)

```
aws/iam/graph/
├── __init__.py
├── cli/
│   ├── Cli__Iam__Graph.py
│   └── verbs/
│       ├── Verb__Iam__Graph__Discover.py
│       ├── Verb__Iam__Graph__Show.py
│       ├── Verb__Iam__Graph__Walk.py
│       ├── Verb__Iam__Graph__Filter.py
│       ├── Verb__Iam__Graph__Delete.py
│       ├── Verb__Iam__Graph__Stats.py
│       └── Verb__Iam__Graph__Snapshots.py
├── service/
│   ├── Iam__Discovery__Orchestrator.py     # pulls IAM state via IAM__AWS__Client (existing)
│   ├── Iam__Graph__Builder.py              # IAM data → graph nodes + edges
│   ├── Iam__Graph__Walker.py               # transitive permission walk
│   ├── Iam__Graph__Filter.py               # the unused/pattern/aws-default predicates
│   ├── Iam__Graph__Vault__Writer.py        # snapshot persistence
│   └── Iam__Graph__Snapshot__Diff.py
├── schemas/                                # Schema__IAM__Graph__Snapshot, Schema__IAM__Node__Role, ...Policy, ...User, ...Group, Schema__IAM__Edge, etc.
├── enums/                                  # Enum__IAM__Node__Type, Enum__IAM__Edge__Type, Enum__IAM__Scope__Breadth
├── primitives/                             # Safe_Str__IAM__Snapshot__Id, etc.
└── collections/                            # List__Schema__IAM__Node__Role, List__Schema__IAM__Edge
```

---

## What you do NOT touch

- Any other surface folder under `aws/` (other than the existing `aws/iam/` package, where you add the `graph/` sub-folder)
- `aws/_shared/` (Foundation-owned)
- CloudTrail integration — Slice F owns CloudTrail; Phase 4 of the brief consumes both, in a v0.2.30 pack
- The SG/App visualisation (Phase 2) — out of scope; this slice is CLI-only
- `iam role/policy ...` existing verbs — unchanged

---

## Acceptance

```bash
# discovery
sg aws iam graph discover --json                                       # → snapshot ID
sg aws iam graph snapshots list                                        # → most recent at top

# filter / show / walk
sg aws iam graph show                                                  # → counts by node type
sg aws iam graph filter --aws-default --json | jq '.candidates | length'
sg aws iam graph filter --unused --days 90 --output /tmp/candidates.json
sg aws iam graph walk arn:aws:iam::123456789012:role/sg-vault-publish --depth 3
sg aws iam graph stats                                                 # → scope-breadth histogram

# delete (gated)
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/candidates.json        # dry-run by default
SG_AWS__IAM__ALLOW_MUTATIONS=1 sg aws iam graph delete --from /tmp/candidates.json --confirm --yes

# snapshot diff after deletion
sg aws iam graph snapshots diff <before> <after> --json | jq '.removed | length'

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/iam/graph/ -v
SG_AWS__IAM__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/iam/graph/ -v
```

Acceptance criterion from the source brief (§Acceptance #5): "At least 30% of AWS-default unused roles deleted in the first cleanup pass." This slice provides the tooling; the actual cleanup pass is operator-driven and reported in a separate Architect debrief after first use.

---

## Deliverables

1. All files under `aws/iam/graph/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/iam/graph/` (with in-memory IAM data fixtures)
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/iam/graph/` (gated)
4. New user-guide page `library/docs/cli/sg-aws/12__iam-graph.md`
5. Update `library/docs/cli/sg-aws/06__iam.md` with a forward-pointer to the `graph` sub-tree
6. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
7. Reality-doc update: extend `team/roles/librarian/reality/aws-and-infrastructure/iam.md`

---

## Risks to watch

- **AWS rate limits on IAM `List*` calls.** First discovery on a large account can hit throttling. Use exponential backoff; cache aggressively within the discovery run.
- **Dry-run as the default for `delete`.** Hard rule. The `--confirm` flag must be passed for any actual deletion. The audit log records both dry-runs and real deletions.
- **AWS-default role detection.** "AWS-default" means roles created by AWS-managed services (Lambda execution roles for AWS-default templates, CodeBuild service roles, etc.). The heuristic: role's TrustPolicy principal is an AWS service AND the role was created by a non-user principal (CreatedBy in CloudTrail). Provide a `--strict-aws-default` flag for stricter matching.
- **Snapshot freshness.** A snapshot diff between two stale snapshots is misleading. Default `discover` always writes a fresh snapshot; `filter` and `delete` refuse snapshots older than 7 days unless `--allow-stale`.
- **Service-linked roles cannot be deleted via IAM API directly.** Filter them out from delete candidates; surface them in `show` with a "service-linked — cannot delete via this tool" tag.
- **Cascading deletions.** Deleting a role attached to active resources (Lambda functions, EC2 instances) breaks them. Pre-flight check: refuse to delete a role with any non-IAM resource using it; require `--force-cascade` to override (and log loudly).

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-iam-graph`

Commit message: `feat(v0.2.29): sg aws iam graph — discovery + cleanup workflow (Phases 1+3)`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator AND request AppSec sign-off (delete-by-filter is a high-blast-radius operation). Do **not** merge yourself.

---

## Cancellation / descope

Independent. Cancelling here defers the IAM cleanup workstream; no other v0.2.29 slice is affected. Phase 4 (evidence-driven recommendations) was already deferred to v0.2.30 and is decoupled from this slice's timeline.
