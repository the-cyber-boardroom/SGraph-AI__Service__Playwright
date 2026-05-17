---
title: "Stable Cross-Doc ID Registry"
file: README.md
maintainer: Librarian
purpose: Mint and track stable IDs that survive file renames. Adopted from the sgai-send pattern; ratified 2026-05-17.
---

# Stable Cross-Doc ID Registry

Stable IDs let documents reference each other independent of file paths. When a brief, debrief, plan, or master-index file moves or gets renamed, the ID stays — references don't break.

**Rule:** IDs apply going forward. We do NOT backfill IDs into pre-2026-05-17 history (Q5 ratified).

---

## ID Prefixes

| Prefix | Owns | Allocator | Format |
|---|---|---|---|
| `M-NNN` | **Migration tasks** — the ontology/taxonomy rollout queue. Replaces the `B-001..B-012` migration entries in `DAILY_RUN.md`. | Librarian | `M-001` … |
| `INC-NNN` | **Incidents** — post-mortems, hot-fix process changes, hard-won rules added to CLAUDE.md (e.g. the `sg-*` security-group prefix block). | Librarian (mints) + originating role (writes) | `INC-001` … |
| `B-NNN` | **Backlog items** — generic "important but not urgent" tasks in `DAILY_RUN.md`. | Librarian | `B-001` … |
| `D-NNNN` | **Debriefs** (optional, low priority) — already implicitly keyed by date in `team/claude/debriefs/`. | Historian | `D-2026-05-17-01` … |

Numbers are sequential within a prefix and **never reused**, even if a task is cancelled.

---

## Active Registry

### Migration (`M-NNN`)

| ID | Title | Status | Owner | Lands in |
|---|---|---|---|---|
| `M-001a` | Fix CLAUDE.md reality-doc + version-file pointers + briefing→onboarding | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-001b` | Refresh `library/catalogue/README.md` (version, endpoint count, pointers) | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-001c` | Create `reality/verified-by.md` | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-001d` | Create this registry | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-002` | Archive flat `v0.1.{12,13,24,29}__what-exists-today.md` + `v0.1.31/` to `reality/_archive/` | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-003` | Create per-domain `index.md` for 9 unmigrated domains (cli/ split into 4 subareas) | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-004` | Split `reality/sg-compute/index.md` (545 lines) into 6 sub-files + cover sheet | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-005` | Roll out `proposed/index.md` to all 11 domains | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-006a` | Rename `library/briefing/` → `library/onboarding/`; update all inbound links | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-006b` | Move `sg_compute/brief/` → `team/comms/briefs/v0.2.25__sg-compute/` | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-007a` | Refresh `library/catalogue/` — 8 live shards, `_snapshots/v0.2.25/`, `_archive/` | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-007b` | Split `library/docs/specs/v0.20.55__schema-catalogue-v2.md` (1,439 lines) | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-007c` | Split `library/docs/specs/v0.20.55__routes-catalogue-v2.md` (1,234 lines) | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-007d` | Strip `═══` H1 banner blocks from the 3 v0.20.55 catalogue specs | ✅ DONE 2026-05-17 | Librarian | this branch |
| `M-013` | Reconcile endpoint count discrepancy (CLAUDE.md says 25, wired routes total 23) | ❌ NOT STARTED | Librarian + Architect | next session |
| `M-014` | VERIFY markers in domain indexes — reconcile against post-BV2.11/BV2.12 deletions of `sgraph_ai_service_playwright/` and `agent_mitmproxy/` packages | ❌ NOT STARTED | Librarian | next session |
| `M-015` | Resolve 19 broken links surfaced by Agent E in `catalogue/findings.md` | ❌ NOT STARTED | Librarian | next session |
| `M-008` | Health scan (continuous) — broken-link walk, naming-violation report | ❌ NOT STARTED | Librarian | weekly cadence |
| `M-009` | Pointer-log entry per code-affecting commit (continuous) | 🟢 ONGOING | Librarian | per session |
| `M-010` | Refresh `verified-by.md` (continuous) | 🟢 ONGOING | Librarian | per session |
| `M-011` | Refresh `catalogue/findings.md` (continuous) | ❌ NOT STARTED | Librarian | per version bump |
| `M-012` | Process `library/docs/_to_process/` inbox (continuous) | 🟢 ONGOING | Librarian | per session |

### Incidents (`INC-NNN`)

| ID | Title | Date | Source |
|---|---|---|---|
| `INC-001` | `sg-*` security-group prefix rejected by AWS `CreateSecurityGroup` | pre-2026-05 | CLAUDE.md rule #14 (precedent: `scripts/provision_ec2.py:83`) |
| `INC-002` | AWS Name tag double-prefix (`elastic-elastic-quiet-fermi`) | pre-2026-05 | CLAUDE.md rule #15 |
| `INC-003` | Oversized Python files: `scripts/{provision_ec2.py (2510 LOC), elastic.py (1335), elastic_lets.py (1210)}`, `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py (1248)`. Rule #22 violations in `__init__.py`: `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py (552 LOC)`, `sg_compute_specs/open_design/cli/__init__.py (228 LOC)`, `sgraph_ai_service_playwright__cli/neko/cli/__init__.py (225 LOC)`. Suspicious: `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py (612 LOC — likely inlined HTML); `team/humans/dinis_cruz/briefs/05/17/.../sg_lab_mvp.py (851 LOC — SCRATCH-grade Python in a brief folder)`. | 2026-05-17 | Surfaced in ontology-proposal §1.5 + catalogue/findings.md; filed per Q6 ratification. Out of Librarian scope to refactor — flagged to Dev. Updated with 2 new `__init__.py` violations + 2 suspicious files surfaced by Agent E. |

### Backlog (`B-NNN`)

| ID | Title | Status |
|---|---|---|
| (Existing backlog in `../DAILY_RUN.md` retains its `B-001..B-012` IDs; new backlog items continue from `B-013`.) | | |

---

## Allocation Procedure

1. Open this file.
2. Next free integer for the relevant prefix.
3. Add a row to the relevant section above with: ID, one-line title, status, owner, target.
4. Reference the new ID from the document being created.
5. Commit in the same change.

When an item is DONE, leave the row in place and change the status; do not delete.
