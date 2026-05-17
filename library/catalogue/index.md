---
title: "Catalogue — Master Index"
file: index.md
shard: index
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Master Index

This file is the entry point for the live catalogue. It maps to 7 sibling shards, each scoped to one concern area. The catalogue is **derived** from the reality tree (`team/roles/librarian/reality/`); when reality and catalogue disagree, reality wins. Catalogue is rewritten freely; reality is append-only-by-domain.

This file replaces the prior flat 9-shard layout (`01__project-overview.md` … `09__team-and-roles.md`) which is now archived under [`_archive/`](_archive/). The layout follows Pattern A from the ontology proposal (§3.6 of [`v0.2.25__ontology-and-taxonomy-proposal.md`](../../team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md)) — stable filenames, frontmatter currency, periodic immutable `_snapshots/v{X.Y.Z}/` freezes.

---

## Map of Shards

| Shard | File | Covers | Read it for |
|-------|------|--------|------------|
| `service` | [`service.md`](service.md) | Playwright browser-automation FastAPI service (now hosted under `sg_compute_specs/playwright/`) — endpoints, route classes, service classes, schemas, dispatcher | Endpoints + service-class layout for the Playwright service |
| `cli` | [`cli.md`](cli.md) | Every top-level CLI namespace exposed via the `sg` entry point: `sg aws {dns,acm,billing,cf,lambda}`, `sg {playwright,firefox,ollama,vault-app,vault-publish,…}`, `sg repl`, legacy `sp` alias | How the Typer tree is wired and which file owns each verb |
| `specs` | [`specs.md`](specs.md) | `sg_compute_specs/` inventory — 15 specs sharing the `Spec__CLI__Builder` (v0.2.6+) contract | Spec-by-spec status, stack purpose, key files |
| `infra` | [`infra/.md`](infra.md) | Docker images, CI workflows, ECR repos, Lambda history, EC2 provisioning, observability stack | Build & deploy surface |
| `tests` | [`tests.md`](tests.md) | Test layout across `tests/`, `sg_compute__tests/`, `sg_compute_specs/*/tests/` — counts, deploy-via-pytest, `*__In_Memory` pattern | Where tests live and how new ones plug in |
| `team` | [`team.md`](team.md) | The 6 agent roles, debrief index, comms structure, human-inbox rules | Onboarding to the role/process model |
| `findings` | [`findings.md`](findings.md) | Health metrics — oversized files, broken-link spot-checks, migration state, last reality update | One-pass repo-health snapshot |

---

## What Changed Since Prior Snapshot

This is the first snapshot under the new shape. No prior snapshot exists.

| Shard | Delta | Notes |
|-------|-------|-------|
| `service` | N/A — first snapshot under new shape | Replaces former `05__playwright-service.md` (which referenced the now-deleted `sgraph_ai_service_playwright/` package). |
| `cli` | N/A — first snapshot under new shape | Replaces former `02__cli-packages.md`, `06__scripts-and-cli.md`. |
| `specs` | N/A — first snapshot under new shape | Novel — no equivalent in the old flat layout. |
| `infra` | N/A — first snapshot under new shape | Replaces former `08__aws-and-infrastructure.md`. |
| `tests` | N/A — first snapshot under new shape | Replaces former `07__testing-patterns.md`. |
| `team` | N/A — first snapshot under new shape | Replaces former `09__team-and-roles.md`. |
| `findings` | N/A — first snapshot under new shape | Novel — adopted from `sgai-tools` (see ontology proposal §4.4 + §4.6). |

Subsequent snapshots will populate this table from a diff between the live shard and `_snapshots/{prior_snapshot}/{shard}.md`.

---

## Snapshot Cadence

- Taken on every minor version bump (`v0.2.x → v0.3.0`).
- Taken before structural rewrites of the live tree.
- Snapshots are `cp -r`, never `mv` — the live tree retains stable filenames.
- Snapshots live under [`_snapshots/v{X.Y.Z}/`](./_snapshots/).

Current snapshot directory: [`_snapshots/v0.2.25/`](_snapshots/v0.2.25/) — the freeze produced alongside the catalogue rewrite on 2026-05-17 against repo commit `ab0c380`.

---

## New-Session Quick-Start (read in order)

1. [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md) — project rules, stack constraints, non-negotiables.
2. [`team/roles/librarian/reality/index.md`](../../team/roles/librarian/reality/index.md) — master domain map (11 domains). Reality is canonical.
3. Root [`version`](../../version) file — current package version (today: `v0.2.25`).
4. [`README.md`](README.md) — catalogue entry point (note: README itself may need a refresh to list the new shards).
5. This file (`index.md`) — orient inside the catalogue graph.
6. The shard relevant to your concern (`service.md`, `cli.md`, etc.).
7. [`team/roles/{role}/ROLE.md`](../../team/roles/) — the role definition matching your task.
8. [`team/comms/`](../../team/comms/) — open briefs / plans / changelog for your area.
9. [`team/claude/debriefs/index.md`](../../team/claude/debriefs/index.md) — per-slice retrospective trail.

---

## Cross-Links

| Destination | Path |
|-------------|------|
| Reality master index | [`team/roles/librarian/reality/index.md`](../../team/roles/librarian/reality/index.md) |
| Reality changelog (pointer log) | [`team/roles/librarian/reality/changelog.md`](../../team/roles/librarian/reality/changelog.md) |
| Reality verified-by | [`team/roles/librarian/reality/verified-by.md`](../../team/roles/librarian/reality/verified-by.md) |
| Ontology proposal | [`team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md`](../../team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md) |
| Stable-ID registry | [`team/roles/librarian/ids/README.md`](../../team/roles/librarian/ids/README.md) |
| Project rules | [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md) |
| Schema catalogue (spec) | [`library/docs/specs/v0.20.55__schema-catalogue-v2.md`](../docs/specs/v0.20.55__schema-catalogue-v2.md) |
| Routes catalogue (spec) | [`library/docs/specs/v0.20.55__routes-catalogue-v2.md`](../docs/specs/v0.20.55__routes-catalogue-v2.md) |
| Debrief index | [`team/claude/debriefs/index.md`](../../team/claude/debriefs/index.md) |
| Onboarding sequence | [`library/onboarding/`](../onboarding/) |
| Archived numbered shards | [`_archive/`](_archive/) |
