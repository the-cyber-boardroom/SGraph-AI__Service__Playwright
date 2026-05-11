# Librarian Brief — Vault Setup and Agentic Team

**Audience:** Librarian agent (and any team member adding to the team folder structure)
**Status:** Required from day 1; not a follow-up
**Repo:** `https://github.com/SG-Compute/SG-Compute__Image-Builder`

This brief covers two foundational concerns that must exist from the first commit:

1. **Vault setup** — how the repo and its workspaces relate to sgit-managed vaults
2. **Agentic team setup** — the `humans/` and `team/roles/` folder structure that mirrors `SG_Send__Deploy`, so the project ships with a working multi-agent collaboration pattern

The principles being honoured: **P13** (visible files), **P14** (sgit is the user's tool; sgi never invokes it), **P12** (workspace as unit of context).

---

## Part 1 — Vault setup

### The principle

sgi treats vaults as **transparent**. From sgi's perspective:

- A workspace is a folder with `state.json` in it
- That folder may or may not be inside a `.sg_vault/`-managed directory
- sgi never reads `.sg_vault/`, never invokes `sgit`, never knows whether the user is using vaults
- The user owns sgit lifecycle: `sgit init`, `sgit commit`, `sgit push`

### What this means for the repo

Three things:

**1. `.gitignore` includes `_vaults/`** from day one:

```gitignore
# Repo-level .gitignore
_vaults/
__pycache__/
*.pyc
.pytest_cache/
dist/
build/
.coverage
.mypy_cache/
.ruff_cache/
*.egg-info/
.venv/
venv/
```

**2. A top-level `_vaults/` folder ships empty** (with a `.gitkeep`) so users have an obvious place to create workspaces. The folder is gitignored so the workspaces inside it never accidentally get committed.

```
SG-Compute__Image-Builder/
├── _vaults/                            ← gitignored, present from day 1
│   └── .gitkeep
└── ...
```

**3. The README documents the vault workflow** at a high level — without sgi having to know any of it:

```markdown
## Working with workspaces

sgi state lives in workspace folders. The convention in this repo is to put
them under `_vaults/`, which is gitignored so workspace contents never get
committed to this repo.

To start a new workspace:

    cd _vaults
    mkdir my-experiment
    cd my-experiment
    sgi init

To version-control a workspace independently (recommended):

    sgit init my-workspace
    cd my-workspace
    sgi init
    # ...do work...
    sgit commit "captured vllm-disk baseline"
    sgit push
```

That's it. sgi remains ignorant of `sgit`. The user's choice to use vaults is just that — a choice.

### Why this works

- **Trust boundary clean:** sgit needs vault keys; sgi never sees them. Compromising sgi doesn't compromise vaults.
- **Workflow flexible:** users can vault some workspaces and not others, depending on sensitivity.
- **Repo light:** the main repo doesn't bloat with workspace contents.
- **Recovery path simple:** a workspace is just files; if sgit metadata gets corrupted, the workspace still functions.

### Failure modes to design against

If a user runs `sgi init` from inside a `.sg_vault/`-managed directory, no special handling is needed. sgi will write `state.json` etc. as visible files. The user's next `sgit commit` will pick them up.

If a user runs `sgi init` from `_vaults/` itself (not a subdirectory), sgi should refuse: "the `_vaults/` directory is a container for workspaces; cd into a subdirectory first." This is a UX safety net, not a hard requirement.

---

## Part 2 — Agentic team setup

The repo ships with a working multi-agent collaboration scaffold from day one. Pattern lifted from `SG_Send__Deploy`. The structure has two halves:

- **`humans/`** — briefs and debriefs from the project lead
- **`team/roles/`** — per-role workspaces for the agentic team

Both are first-class folders in the repo, committed alongside code.

### `humans/` layout

```
humans/
└── dinis_cruz/
    ├── briefs/                         ← prompts, requirements, decisions FROM Dinis
    │   ├── 05/                          ← month-based folders
    │   │   ├── 11/                      ← day-based folders
    │   │   │   ├── v0.1.0__brief-pack__sgi-v1.md
    │   │   │   ├── v0.1.0__decision__ssh-over-ssm.md
    │   │   │   └── ...
    │   │   └── 12/
    │   └── 06/
    │
    ├── debriefs/                       ← session outcomes, summaries TO Dinis
    │   ├── 05/
    │   │   └── 11/
    │   │       ├── v0.1.0__debrief__architecture-session.md
    │   │       └── ...
    │   └── ...
    │
    └── feedback-to-sg-compute.md       ← running list of sg-compute feedback items
```

Naming convention for briefs and debriefs:

```
v<version>__<type>__<topic-slug>.md
```

Examples:
- `v0.1.0__brief-pack__sgi-v1.md`
- `v0.1.0__decision__ssh-over-ssm.md`
- `v0.1.0__debrief__architecture-session.md`
- `v0.1.0__technical-brief__ec2-ephemeral-launcher.md`
- `v0.1.0__research-brief__zstd-vs-gzip-payloads.md`

Brief types:
- `brief` — a single-purpose ask
- `arch-brief` — architecture decision
- `dev-brief` — development task
- `research-brief` — investigation/exploration
- `technical-brief` — implementation detail
- `decision` — recorded outcome of a debate
- `debrief` — session outcome / what was done

### `team/roles/` layout

Six roles, mirroring SG_Send__Deploy. Each role has a self-contained workspace:

```
team/
└── roles/
    ├── conductor/
    │   ├── README.md                   ← role definition
    │   ├── reviews/                    ← decisions, status reports
    │   └── master-index.md             ← cross-role index
    │
    ├── architect/
    │   ├── README.md
    │   ├── reviews/
    │   │   └── 05/
    │   │       └── 11/
    │   │           └── v0.1.0__architecture-review__sgi-v1.md
    │   └── decisions/                  ← long-lived architectural decisions
    │
    ├── developer/
    │   ├── README.md
    │   ├── reviews/
    │   │   └── 05/
    │   │       └── 11/
    │   │           └── v0.1.0__implementation-plan__sgi-v1.md
    │   ├── plans/                      ← per-milestone implementation plans
    │   └── notes/                      ← scratch
    │
    ├── devops/
    │   ├── README.md
    │   ├── reviews/
    │   │   └── 05/
    │   │       └── 11/
    │   │           └── v0.1.0__ci-pipeline-setup__sgi-v1.md
    │   └── runbooks/                   ← operational guides
    │
    ├── appsec/
    │   ├── README.md
    │   ├── reviews/
    │   ├── threat-models/              ← per-spec threat models
    │   └── findings/                   ← active security concerns
    │
    └── librarian/
        ├── README.md
        ├── reviews/
        │   └── 05/
        │       └── 11/
        │           └── v0.1.0__master-index__brief-pack-and-team-bootstrap.md
        ├── catalogues/                 ← what exists, where
        └── master-index.md             ← top-level navigation
```

### Role README templates

Each role's `README.md` is a stable definition of the role's scope, responsibilities, and outputs. Template:

```markdown
# Role: <Role Name>

## Purpose
One paragraph: why this role exists in the team.

## Scope
- What this role IS responsible for
- What this role IS NOT responsible for

## Inputs
- Human briefs from `humans/dinis_cruz/briefs/`
- Cross-role artefacts (which roles' outputs feed in)
- External context (which repos, which docs)

## Outputs
- Where this role writes artefacts (`reviews/`, `plans/`, etc.)
- What downstream roles consume those artefacts

## Cadence
- When this role activates (per-PR, per-milestone, ad-hoc)
- Who triggers the role (human, conductor, automatic)

## Boundary conditions
- When this role escalates to another role
- When this role is read-only vs decision-making
```

#### Specifics per role

**Conductor** — Coordinates the team. Reads new briefs, decides which role(s) should engage, summarises outcomes back to Dinis. Doesn't write code or architecture; manages flow.

**Architect** — Owns the design integrity. Reviews PRs for principle violations (the 21 from [01__principles/principles.md](../01__principles/principles.md)). Produces architecture reviews when new components are designed. Has veto on principle violations.

**Developer** — Writes the code. Implements milestones from the implementation plan. Produces per-milestone implementation plans before starting work. Files debriefs after merging.

**DevOps** — Owns CI/CD, secrets, release pipeline, observability (see [10__dev-ops/dev-ops-brief.md](../10__dev-ops/dev-ops-brief.md)). Owns the `Makefile`. Owns the GitHub Actions workflows.

**AppSec** — Owns security review of each spec. Maintains per-spec threat models. Reviews `SECURITY.md` content in every bundle's sidecar. Reviews strip-mode keep-lists for security implications.

**Librarian** — Maintains the index. Cross-links briefs and debriefs. Ensures naming conventions are honoured. Maintains `master-index.md` files at top and per-role level.

### Bootstrap content for v0.1.0

The repo ships with placeholder reviews for each role that mirror what the team would produce after reading this brief pack:

```
team/roles/architect/reviews/05/11/v0.1.0__architecture-review__brief-pack-acceptance.md
team/roles/developer/reviews/05/11/v0.1.0__implementation-plan__brief-pack-acceptance.md
team/roles/devops/reviews/05/11/v0.1.0__ci-pipeline-bootstrap.md
team/roles/librarian/reviews/05/11/v0.1.0__master-index__brief-pack-bootstrap.md
```

These are stubs initially. They get filled in as the team's first sessions run. The point: the folder structure is there from PR #1 so the team has somewhere to put their work.

### Master index files

Two levels of index:

**`team/roles/librarian/master-index.md`** — top-level navigation (example shape, filled in as the team produces work):

```markdown
# SG-Compute Image Builder — Master Index

## Briefs (latest)
- v0.1.0 — Brief Pack (this pack)

## Reviews (latest per role)
- Architect: `../architect/reviews/05/11/v0.1.0__architecture-review__brief-pack-acceptance.md`
- Developer: `../developer/reviews/05/11/v0.1.0__implementation-plan__brief-pack-acceptance.md`
- DevOps: `../devops/reviews/05/11/v0.1.0__ci-pipeline-bootstrap.md`
- ...

## Active concerns
- (filled in as work progresses)
```

**Per-role `master-index.md`** — what this role has produced:

```markdown
# Architect — Master Index

## Latest reviews
- v0.1.0 — brief-pack-acceptance — 11 May 2026
- ...

## Decisions
- SSH over SSM — 11 May 2026
- Workspace folders, not hidden dirs — 11 May 2026
- ...

## Active design questions
- (open items)
```

Indexes are maintained by the Librarian on each merge. The Librarian's CI job (optional) can lint that referenced files exist.

### Feedback to sg-compute

A running list of feedback items lives at `humans/dinis_cruz/feedback-to-sg-compute.md`. This is the dog-fooding output: every time sgi's `Exec_Provider__Sg_Compute` falls back to text parsing because `sg lc` lacks a `--json` flag, the item gets added here.

Template:

```markdown
# Feedback for sg-compute team

This file accumulates suggestions for the sg-compute team based on
sgi's experience consuming `sg lc *` via shell-out.

## Open items

### High priority

#### `sg lc list --json` should output structured JSON
**Why:** sgi shells out to this and currently parses table output.
**Impact:** Brittle; breaks when sg-compute's table format changes.
**Proposed shape:**
    [
      {"name": "compute-1", "instance_id": "i-xxx", "state": "running",
       "region": "eu-west-2", "instance_type": "g5.xlarge", ...}
    ]
**First observed:** 2026-05-11 during M2 (workspace + CLI bootstrap)

### Medium priority

...

## Resolved items

(Items get moved here when sg-compute ships the change. Each entry retains its
history for traceability.)
```

This file is the deliverable to the sg-compute team. It's reviewed periodically and items get prioritised based on impact.

---

## First steps for the Librarian agent

1. Read this brief in full
2. Read [01__principles/principles.md](../01__principles/principles.md) — especially P12, P13, P14
3. Read [11__librarian/librarian-brief.md](librarian-brief.md) (this file)
4. Read the existing `SG_Send__Deploy/team/roles/librarian/` directory for reference patterns
5. Create the folder structure described above as part of M0
6. Write the role README files using the template
7. Create initial `master-index.md` files
8. Commit `_vaults/.gitkeep` and the `.gitignore` entry
9. Hand over to the Conductor for ongoing coordination

---

## Failure modes to design against

**The team folders grow into a graveyard.** Mitigation: every review file has a date. Master indexes prune anything older than 90 days (move to `archive/` with date prefix). Active concerns are time-boxed.

**Briefs and debriefs drift out of sync.** Mitigation: every debrief references the brief it came from (by version + slug). The Librarian's CI job verifies these links resolve.

**Naming conventions get lax.** Mitigation: a `scripts/lint_briefs.py` script checks the naming convention. Run as part of `pr.yml`.

**The "Librarian" never engages.** Mitigation: a weekly cadence — the Conductor pings the Librarian to update master indexes. Indexes have a "last reviewed" date; if it's > 14 days, flag it.

---

## Connection to the broader pattern

This setup mirrors `SG_Send__Deploy` deliberately. Anyone who has worked in that repo finds the same shape here, and patterns transfer. As more SG-* repos are created, they all get the same scaffold, and an engineer (or agent) moving between them encounters identical structure.

The structure is intentionally low-tech. It's folders and markdown. It's grep-able, git-blameable, and survives any tooling change. Vault-ification is an overlay; the structure works without it.
