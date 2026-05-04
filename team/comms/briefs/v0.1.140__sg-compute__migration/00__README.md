# v0.1.140 — SG/Compute Migration

**Status:** PROPOSED
**Owner:** UI Architect (frontend track) + Architect (backend track)
**Audience:** two parallel Sonnet teams — backend and frontend
**Source brief:** [`sources/voice-memo-30-apr.md`](sources/voice-memo-30-apr.md) (verbatim voice memo)
**Conversation that produced this:** UI Architect ↔ Human, 2026-05-02
**Repo target (eventual):** `sgraph-ai/SG-Compute` — but this first refactoring phase stays in `the-cyber-boardroom/SGraph-AI__Service__Playwright`

---

## Why this brief exists

The codebase has grown well beyond "a Playwright service." It now provisions and manages ephemeral compute (today: AWS EC2; tomorrow: K8s, GCP, local) running 8+ different application stacks (Firefox, Docker, Podman, Elastic+Kibana, Prometheus+Grafana, OpenSearch, VNC, Neko, plus the Playwright service itself). The original naming (`sgraph_ai_service_playwright*`, "stack" used to mean a single instance, "plugin" used to mean an application type) no longer matches what we're building.

This brief commissions the renaming AND the structural refactor that makes the renaming worthwhile: a clean SDK/catalogue split, a typed spec contract, a platforms abstraction, and a fractal composition rule that lets specs build on each other.

---

## The decision in 60 seconds

| What | Value |
|------|-------|
| **Product name** | SG/Compute (long form: "SG/Compute — Ephemeral Compute") |
| **Two PyPI packages** | `sg-compute` (the SDK) + `sg-compute-specs` (the catalogue) |
| **Python imports** | `sg_compute`, `sg_compute_specs` |
| **Top-level folders** | `sg_compute/`, `sg_compute_specs/` |
| **CLI command** | `sg-compute` (with verbs: `node`, `pod`, `spec`, `stack`) |
| **Taxonomy** | **Node** (single instance) · **Pod** (container in a node) · **Spec** (recipe for a node) · **Stack** (multi-node combination) |
| **Platforms (was "substrates")** | `sg_compute/platforms/ec2/` today; future: `k8s/`, `gcp/`, `local/` |
| **Repo (this phase)** | Stay in `the-cyber-boardroom/SGraph-AI__Service__Playwright` |
| **Repo (eventual)** | `sgraph-ai/SG-Compute` |
| **PyPI availability** | All four candidate names confirmed free on 2026-05-02 |

---

## What "self-contained spec" means

A spec is a single folder under `sg_compute_specs/<name>/` containing **everything** that defines that node type:

```
sg_compute_specs/firefox/
    manifest.py                # the typed catalogue entry — single source of truth
    version                    # semver, owned by the spec
    api/                       # FastAPI routes specific to this spec
    core/                      # spec-specific logic (orchestration, health, lifecycle)
    cli/                       # Typer sub-commands for this spec
    schemas/                   # Type_Safe request/response schemas
    user_data/                 # cloud-init / EC2 user-data builder
    ui/                        # web components: card + detail + sub-panels
    dockerfile/                # image (optional — only if the spec ships a container)
    assets/                    # icon SVG, screenshots (optional)
    tests/                     # spec-level tests (excluded from the wheel by pyproject)
```

Specs leverage `sg_compute` for the heavy lifting (EC2 launch, security groups, health polling, user-data assembly, schema bases) and only own the bits that are genuinely spec-specific. The success metric: **a new trivial spec is < 6 files**, and a pure-JSON spec is **2 files** (`manifest.json` + `version`).

---

## What's in each file of this brief

| File | For whom | Purpose |
|------|----------|---------|
| [`00__README.md`](00__README.md) | Everyone | This file — strategy + index |
| [`01__architecture.md`](01__architecture.md) | Both teams | The single source of truth for the taxonomy, the two-package split, the platforms layer, the spec contract, the fractal-composition rule, and the legacy-mapping table. **Read this before reading the team plans.** |
| [`10__backend-plan.md`](10__backend-plan.md) | Backend Sonnet team | Detailed work breakdown, one phase per checklist, with file paths and acceptance criteria. |
| [`20__frontend-plan.md`](20__frontend-plan.md) | Frontend Sonnet team | Same shape, frontend-scoped. |
| [`30__migration-phases.md`](30__migration-phases.md) | Conductor / Architect | Sequencing across both teams. Which phases block which. Cadence and exit criteria. |
| [`sources/voice-memo-30-apr.md`](sources/voice-memo-30-apr.md) | Reference | Verbatim voice memo that started this. Preserved for historical context. |

---

## Out of scope (explicitly)

- **Repo extraction.** Not in this phase. After phase 8 (PyPI smoke test) we revisit and decide on `sgraph-ai/SG-Compute` migration timing.
- **Cosmetic UI rename `sp-cli-*` → `sg-compute-*`.** Deferred to phase 9 (after the API/contract migration is stable).
- **Legacy code deletion.** The existing `sgraph_ai_service_playwright*` packages keep working until each piece migrates. No mass deletion in this brief.
- **Light mode, mobile, A11y deep work.** Out of scope for this naming/structural refactor.
- **Production deployment changes.** Lambda packaging, ECR pushes, CI workflows — all keep working unchanged in phases 1-2. Phase 8 revisits.

---

## Constraints that bind both teams

These are non-negotiable across every phase:

- **Type_Safe everywhere.** No Pydantic. No raw `str / int / list / dict` attributes. No Literals — fixed-value sets are `Enum__*`.
- **One class per file.** Empty `__init__.py`. Schemas, primitives, enums, and collection subclasses each get their own file.
- **`osbot-aws` for AWS.** No direct boto3 (existing carve-outs noted in the architecture doc).
- **Routes have no logic** — pure delegation to a service class.
- **No build toolchain on the frontend.** Native ES modules. Plain CSS. Web Components with Shadow DOM.
- **No emoji in source files** unless the existing convention already uses them (plugin card icons stay).
- **Branch naming:** feature branches `claude/{description}-{session-id}`. Never push to dev directly.
- **Reality doc is updated in the same commit as the code.** Every code change updates the relevant `team/roles/librarian/reality/{domain}/index.md` (today: only `host-control/` is migrated; for other domains, append to the relevant `v0.1.31/NN__*.md` slice or — once migrated — to the new domain index).

---

## Lifecycle of this brief

1. **Architect / UI Architect file the topic reviews** under `team/roles/{architect|ui-architect}/reviews/MM/DD/` before either team starts implementation.
2. **Phase 1 lands as one PR** (the small, isolated rename). All later phases get their own PR.
3. **Each phase ends with a debrief** under `team/claude/debriefs/`, indexed in `index.md`, with the closing-commit hash.
4. **The Librarian** appends a pointer entry to `team/roles/librarian/reality/changelog.md` for every spec / platform / package change.
5. **When phase 9 closes**, this brief moves to `team/comms/briefs/archive/v0.1.140__sg-compute__migration__{closing-commit}/`.

---

## Read order

If you are a Sonnet team starting this work right now:

1. Read this README (you are here).
2. Read [`01__architecture.md`](01__architecture.md) in full — both teams.
3. Read your team's plan: backend → [`10__backend-plan.md`](10__backend-plan.md); frontend → [`20__frontend-plan.md`](20__frontend-plan.md).
4. Read [`30__migration-phases.md`](30__migration-phases.md) to know what blocks what across teams.
5. Skim the voice memo at [`sources/voice-memo-30-apr.md`](sources/voice-memo-30-apr.md) for context on why "Node / Pod / Spec / Stack."
6. Then start phase 1.
