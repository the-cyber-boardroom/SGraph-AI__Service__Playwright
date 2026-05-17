---
title: "Library Catalogue — SG Playwright Service"
file: README.md
shard: index-meta
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
status: LIVE — 8 stable-filename shards refreshed each session. The 9 legacy numbered files moved to `_archive/` under M-007a on 2026-05-17. Immutable snapshots under `_snapshots/v{X.Y.Z}/`.
---

# Library Catalogue — SG Playwright Service

The SG Playwright Service is a browser-automation API (FastAPI + Playwright) that also
hosts a CLI/HTTP control plane for ephemeral cloud stacks (EC2, Elastic/Kibana,
OpenSearch, Prometheus) and a LETS pipeline that indexes CloudFront logs into Elasticsearch.
It runs identically on laptop, CI, Claude Web, Fargate, and AWS Lambda.

**Current version:** `v0.2.25` (root `version`)
**Master shard:** [`index.md`](index.md) — start here.
**Reality docs:** [`team/roles/librarian/reality/index.md`](../../team/roles/librarian/reality/index.md) — master domain map (11 domains)

---

## Map of Shards (live — refreshed each session)

| File | What it covers | Who reads it |
|------|---------------|--------------|
| [`index.md`](index.md) | Master index + map-of-maps + new-session quick-start + cross-links | Everyone — read first |
| [`service.md`](service.md) | Playwright service: endpoints, schemas, service classes, step actions | Dev touching the Playwright service |
| [`cli.md`](cli.md) | All CLI namespaces (`sp`, `sg compute`, `sg aws`, `sg repl`) + per-package map | Dev adding/extending CLI |
| [`specs.md`](specs.md) | `sg_compute_specs/` inventory (15 specs) + Spec__CLI__Builder pattern | Dev adding a new spec |
| [`infra.md`](infra.md) | Docker images, CI workflows, ECR, Lambda (retired), EC2, observability | DevOps / Architect |
| [`tests.md`](tests.md) | Test layout, counts, no-mocks rule, in-memory pattern, deploy-via-pytest | Dev writing new tests |
| [`team.md`](team.md) | 6 agent roles, debrief index, human inbox rules, comms structure | All agents |
| [`findings.md`](findings.md) | Health metrics: oversized files, broken links, open `M-NNN`, last reality update | Librarian (continuous) |

Frontmatter on every shard declares `as_of:` so readers see currency at a glance.

---

## Snapshots & Archive

- [`_snapshots/v0.2.25/`](_snapshots/v0.2.25/) — first immutable freeze of the live shards (2026-05-17, commit ab0c380). Pattern: `cp -r` of the live tree on every minor version bump.
- [`_archive/`](_archive/) — the 9 legacy numbered files (`01__project-overview.md` … `09__team-and-roles.md`) preserved verbatim. See `_archive/README.md`.

---

## New-Session Quick-Start (read in order)

1. `/.claude/CLAUDE.md` — project rules, stack constraints, non-negotiables
2. [`team/roles/librarian/reality/index.md`](../../team/roles/librarian/reality/index.md) — master domain map → drill into the relevant `{domain}/index.md`
3. `version` (repo root) — current package version (today: `v0.2.25`)
4. [`index.md`](index.md) — master catalogue shard with the navigation map
5. The catalogue shard for your concern area (`service.md` / `cli.md` / `specs.md` / `infra.md` / `tests.md` / `team.md`)
6. `team/roles/{role}/ROLE.md` — your role's responsibilities
7. `team/comms/` — any open briefs or plans for your area
8. `team/claude/debriefs/index.md` — what each prior slice delivered

---

## Key Cross-Links

| Destination | Path |
|-------------|------|
| Reality master index | [`team/roles/librarian/reality/index.md`](../../team/roles/librarian/reality/index.md) |
| Reality changelog | [`team/roles/librarian/reality/changelog.md`](../../team/roles/librarian/reality/changelog.md) |
| Verified-by log | [`team/roles/librarian/reality/verified-by.md`](../../team/roles/librarian/reality/verified-by.md) |
| Project rules | `/.claude/CLAUDE.md` |
| Testing guide | [`library/guides/v3.1.1__testing_guidance.md`](../guides/v3.1.1__testing_guidance.md) |
| Schema catalogue (spec) | [`library/docs/specs/v0.20.55__schema-catalogue-v2.md`](../docs/specs/v0.20.55__schema-catalogue-v2.md) |
| Routes catalogue (spec) | [`library/docs/specs/v0.20.55__routes-catalogue-v2.md`](../docs/specs/v0.20.55__routes-catalogue-v2.md) |
| Debrief index | [`team/claude/debriefs/index.md`](../../team/claude/debriefs/index.md) |
| Open plans | `team/comms/plans/` |
| Onboarding sequence | [`library/onboarding/`](../onboarding/) |
| Ontology proposal | [`team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md`](../../team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md) |
| Librarian ID registry | [`team/roles/librarian/ids/README.md`](../../team/roles/librarian/ids/README.md) |
