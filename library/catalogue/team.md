---
title: "Catalogue — Team & Process"
file: team.md
shard: team
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Team & Process

Six agent personas share this codebase. Always pick the role that matches the task before starting. The role definitions are the canonical source — this shard is a map.

---

## The Six Roles (`team/roles/`)

| Role | Owns | ROLE.md |
|------|------|---------|
| **Architect** | API contracts, schemas, architectural boundaries. Sign-off on the schema/route catalogues and the `Spec__CLI__Builder` contract. | [`team/roles/architect/ROLE.md`](../../team/roles/architect/ROLE.md) |
| **Dev** | Implementation, tests, refactors. Lands code and updates the relevant reality-domain `index.md` in the same commit. | [`team/roles/dev/ROLE.md`](../../team/roles/dev/ROLE.md) |
| **QA** | Test strategy, deploy-via-pytest assertions, gated-Chromium integration coverage, smoke tests. | [`team/roles/qa/ROLE.md`](../../team/roles/qa/ROLE.md) |
| **DevOps** | CI workflows, Docker images, ECR / Docker Hub publishing, EC2 provisioning helpers, Lambda artefacts (where they still exist). | [`team/roles/devops/ROLE.md`](../../team/roles/devops/ROLE.md) |
| **Librarian** | Reality doc, catalogue, cross-references, ID registry, ontology rollout (M-NNN migration queue). | [`team/roles/librarian/ROLE.md`](../../team/roles/librarian/ROLE.md) |
| **Historian** | Decision log, debrief index, phase summaries, commit-hash backfill in the debrief index. | [`team/roles/historian/ROLE.md`](../../team/roles/historian/ROLE.md) |

Role-shared README: [`team/roles/README.md`](../../team/roles/README.md).

---

## Where Each Role's Output Lives

| Role | Primary output paths |
|------|----------------------|
| Architect | `library/docs/specs/`, `library/docs/research/`, `team/roles/architect/reviews/` |
| Dev | `sg_compute/`, `sg_compute_specs/`, `sgraph_ai_service_playwright__cli/`, `tests/`, `sg_compute__tests/` |
| QA | `tests/{ci,integration,deploy,local}/`, `library/guides/v3.1.1__testing_guidance.md`, `team/comms/qa/` |
| DevOps | `.github/workflows/`, `scripts/provision_*.py`, `docker/`, `sg_compute_specs/*/Dockerfile` |
| Librarian | `team/roles/librarian/reality/`, `library/catalogue/`, `team/roles/librarian/ids/`, `team/roles/librarian/reviews/` |
| Historian | `library/reference/v{ver}__decisions-log.md`, `team/claude/debriefs/index.md`, `library/roadmap/phases/` |

---

## Reality-Doc Update Obligation

When code lands, the author updates the relevant reality-domain `index.md` in the same commit. The 11 domains live under [`team/roles/librarian/reality/`](../../team/roles/librarian/reality/) — see [`reality/index.md`](../../team/roles/librarian/reality/index.md) for the master map. The Librarian verifies, fills gaps, and splits files when they exceed ~300 lines.

| Code area | Domain (when migration completes) |
|-----------|-----------------------------------|
| Playwright service | `playwright-service/` (PENDING — current shim `_archive/v0.1.31/01__playwright-service.md`) |
| SG/Compute SDK + specs | `sg-compute/` (ACTIVE) |
| Host control plane | `host-control/` (DONE — pilot) |
| CLI, LETS, UI, Vault, Infra, QA, Security, agent-mitmproxy | PENDING — current shims in `_archive/v0.1.31/` |

---

## Debrief System

- **Index:** [`team/claude/debriefs/index.md`](../../team/claude/debriefs/index.md) — chronological, most-recent-first.
- **Files:** `team/claude/debriefs/{date}__{slice-name}.md`. One per work slice.
- **Classification:** every debrief tags failures as **good failure** (surfaced early, caught by tests, informed a better design) or **bad failure** (silenced, worked around, or re-introduced — implicit follow-up request).
- **Commit hash backfill:** the Historian chases stragglers and updates the index once the Dev commit lands.
- **Session handover:** when wrapping a session, follow [`team/claude/debriefs/SESSION_HANDOVER_GUIDE.md`](../../team/claude/debriefs/SESSION_HANDOVER_GUIDE.md) — meta-template defines required sections, naming, gathering steps.

Recent handover bundles live in their own subdirs: `v0.1.118-caddy-handover/`, `v0.1.96-handover/`, `vnc-handover/`.

---

## Communication Channels (`team/comms/`)

| Subdir | Purpose |
|--------|---------|
| `team/comms/briefs/` | Cross-role background briefs and proposals. Time-bucketed by version (e.g. `v0.2.25__sg-compute/`). 170+ files; dominant home for WORK-kind documents. |
| `team/comms/plans/` | Numbered execution plans for multi-slice work. |
| `team/comms/changelog/` | Cross-role change log. |
| `team/comms/qa/` | QA findings. |

---

## Human Inbox Rules (CRITICAL)

- `team/humans/dinis_cruz/briefs/` — **HUMAN-ONLY. Agents MUST NEVER create files here.** (CLAUDE.md rule #23)
- `team/humans/dinis_cruz/debriefs/` — **HUMAN-ONLY. Agents MUST NEVER edit files here.** (CLAUDE.md rule #24)
- Agent scratch outputs go to: `team/humans/dinis_cruz/claude-code-web/{MM}/{DD}/{HH}/`. Promote to `team/comms/` or `team/roles/{role}/reviews/` once formalised.

---

## Stable Cross-Doc IDs (adopted 2026-05-17)

| Prefix | Owns | Allocator |
|--------|------|-----------|
| `M-NNN` | Migration tasks (M-001 … M-012 in the registry) | Librarian |
| `INC-NNN` | Incidents (e.g. `INC-001` `sg-*` SG-name block, `INC-003` oversized Python files) | Librarian mints, originating role writes |
| `B-NNN` | Backlog items in `DAILY_RUN.md` | Librarian |
| `D-NNNN` | Debriefs (optional) | Historian |

Registry: [`team/roles/librarian/ids/README.md`](../../team/roles/librarian/ids/README.md).

---

## Branch and Commit Rules

| Rule | Value |
|------|-------|
| Default branch | `dev` |
| Branch naming | `claude/{description}-{session-id}` |
| Agents push to `dev`? | **NO** — open a PR from the feature branch |
| Commit style | `type(scope): description` |

---

## Cross-Links

- Roles overview: [`team/roles/README.md`](../../team/roles/README.md)
- Librarian DAILY_RUN: [`team/roles/librarian/DAILY_RUN.md`](../../team/roles/librarian/DAILY_RUN.md)
- ID registry: [`team/roles/librarian/ids/README.md`](../../team/roles/librarian/ids/README.md)
- Ontology proposal (rationale for this shape): [`team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md`](../../team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md)
- Project rules: [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md)
