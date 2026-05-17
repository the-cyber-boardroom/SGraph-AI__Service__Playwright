---
title: "Catalogue — Findings"
file: findings.md
shard: findings
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Findings

Repo-health snapshot — oversized files, broken-link spot-check, migration progress, ID-registry state. Computed against working tree at root commit `ab0c380` (dev tip), branch `claude/setup-librarian-agent-r9azr`. Adopted from the `sgai-tools` pattern (ontology proposal §4.4).

---

## Markdown — Volume & Health

| Metric | Value |
|--------|------:|
| Total `.md` files | **724** |
| `.md` files > 300 lines | **97** |

> The 300-line threshold is the fractal-growth rule (CLAUDE.md / `library/guides/v0.2.15__markdown_doc_style.md`). 97 violations is high but the bulk live in three categories: dev-pack guides, archived reality monoliths, and architect plan briefs.

### Top 10 oversized markdown files

| Lines | Path |
|------:|------|
| 1,943 | `team/humans/dinis_cruz/claude-code-web/05/15/08/architect__sg-aws-dns__plan.md` |
| 1,454 | `library/guides/v3.28.0__safe_primitives.md` |
| 1,285 | `library/guides/v3.1.1__testing_guidance.md` |
| 1,161 | `library/docs/specs/v0.20.55__ci-pipeline.md` |
| 858 | `library/guides/v3.63.4__type_safe.md` |
| 828 | `library/guides/v3.63.3__collections_subclassing.md` |
| 805 | `library/dev_packs/v0.1.101__mvp-of-admin-and-user-ui/03__ui-design-and-components.md` |
| 756 | `library/dev_packs/v0.1.111__ui-refactor-to-use-vault/03__vault-integration.md` |
| 750 | `library/docs/specs/v0.2.6__authoring-a-new-top-level-spec.md` |
| 740 | `team/humans/dinis_cruz/briefs/04/18/arch__layered-dynamic-code-fastapi-runtime-v4.md` |

The top entry is SCRATCH content (`team/humans/dinis_cruz/claude-code-web/`) that should be promoted to WORK or REFERENCE — ontology proposal §1.6. The two `library/docs/specs/v0.20.55__*-catalogue-v2.md` files (1,234 and 1,439 lines) are tracked under M-007b / M-007c.

---

## Python — Oversized Files (over 500 LOC)

### Top 10

| Lines | Path | Notes |
|------:|------|-------|
| 2,510 | `scripts/provision_ec2.py` | `INC-003` (Dev scope) |
| 1,335 | `scripts/elastic.py` | `INC-003` |
| 1,248 | `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py` | `INC-003` |
| 1,210 | `scripts/elastic_lets.py` | `INC-003` |
| 851 | `team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/sg_lab_mvp.py` | SCRATCH-grade Python in a brief folder — VERIFY whether this should live elsewhere. |
| 790 | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` | Under threshold but trending; spec is EXPERIMENTAL and likely to grow. |
| 678 | `sgraph_ai_service_playwright__cli/elastic/service/Elastic__Service.py` | |
| 664 | `scripts/observability_opensearch.py` | |
| 635 | `sg_compute_specs/vault_app/service/Vault_App__Service.py` | |
| 612 | `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` | VERIFY: an `Index` route at 612 lines is surprising; likely contains the static "Try it out" HTML inline. |

---

## `__init__.py` Rule Violations (CLAUDE.md rule #22)

The rule mandates empty `__init__.py`. Non-empty files found:

| Lines | Path | Status |
|------:|------|--------|
| 552 | `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` | `INC-003` — VIOLATES rule #22 |
| 228 | `sg_compute_specs/open_design/cli/__init__.py` | VIOLATES — newly surfaced |
| 225 | `sgraph_ai_service_playwright__cli/neko/cli/__init__.py` | VIOLATES — newly surfaced |
| 7 | `sg_compute_specs/playwright/core/__init__.py` | Borderline (7 lines); below the 5-line filter used for the headline scan. VERIFY contents. |

**Action:** The `open_design` and `neko` `__init__.py` files were not previously flagged in `INC-003`. The Librarian will append them to the registry next session.

---

## Reality Migration Progress

| Metric | Value |
|--------|------:|
| Total domains in master map | 11 |
| Domains with `{domain}/index.md` (migrated) | **7** (`agent-mitmproxy`, `cli`, `host-control`, `playwright-service`, `sg-compute`, `ui`, `vault`) |
| Domains with `{domain}/proposed/` | 7 (same as above) |
| Domains still on `_archive/v0.1.31/` shim | 4 (`infra`, `lets`, `qa`, `security`) |
| Archived flat snapshots in `_archive/` | 4 (`v0.1.12,13,24,29`) + the `v0.1.31/` numbered-parts dir |

The reality master map at `team/roles/librarian/reality/index.md` declares "Last updated: 2026-05-02" and "Domains migrated: 1 (`host-control/` — pilot)" — that header is stale: 7 domains have an `index.md` on disk today. VERIFY and refresh the header counts next session.

---

## Open Migration Tasks (`M-NNN` — from `team/roles/librarian/ids/README.md`)

| ID | Title | Status |
|----|-------|--------|
| `M-001a..d` | Phase 1 (CLAUDE.md, README, verified-by, ids registry) | DONE 2026-05-17 |
| `M-002` | Archive flat `v0.1.{12,13,24,29}` + `v0.1.31/` to `reality/_archive/` | IN PROGRESS |
| `M-003` | Create per-domain `index.md` for 9 unmigrated domains | IN PROGRESS (7 of 11 done, 4 remaining) |
| `M-004` | Split `reality/sg-compute/index.md` (was 545 lines) into sub-files | IN PROGRESS (per-area files exist; main index now 98 lines) |
| `M-005` | Roll out `proposed/index.md` to all 11 domains | IN PROGRESS |
| `M-006a` | Rename `library/briefing/` → `library/onboarding/` | IN PROGRESS |
| `M-006b` | Move `sg_compute/brief/` → `team/comms/briefs/v0.1.162__sg-compute/` | IN PROGRESS |
| `M-007a` | Refresh `library/catalogue/` — 8 live shards + `_snapshots/v0.2.25/` + `_archive/` | **IN PROGRESS — this slice** |
| `M-007b` | Split `library/docs/specs/v0.20.55__schema-catalogue-v2.md` | IN PROGRESS |
| `M-007c` | Split `library/docs/specs/v0.20.55__routes-catalogue-v2.md` | IN PROGRESS |
| `M-007d` | Strip `═══` H1 banner blocks from the 3 v0.20.55 catalogue specs | IN PROGRESS |
| `M-008` | Health scan (continuous) | NOT STARTED — this shard is the first artefact |
| `M-009` | Pointer-log entry per code-affecting commit | ONGOING |
| `M-010` | Refresh `verified-by.md` | ONGOING |
| `M-011` | Refresh `catalogue/findings.md` per version bump | **STARTED — this file** |
| `M-012` | Process `library/docs/_to_process/` inbox | ONGOING |

---

## Broken-Link Spot-Check (REALITY tree only)

Scope: every `.md` under `team/roles/librarian/reality/`. Relative `[text](path)` links only (http/mailto/anchor-only skipped).

> **This is a spot-check, not exhaustive.** Repo-wide link walking is M-008 (`NOT STARTED`).

| Metric | Value |
|--------|------:|
| Links checked | 218 |
| Broken | **19** |

### Broken links (full list)

```
team/roles/librarian/reality/index.md                          -> lets/index.md
team/roles/librarian/reality/index.md                          -> infra/index.md
team/roles/librarian/reality/index.md                          -> qa/index.md
team/roles/librarian/reality/index.md                          -> security/index.md
team/roles/librarian/reality/host-control/index.md             -> ../../../humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__container-runtime-abstraction.md
team/roles/librarian/reality/host-control/index.md             -> ../infra/index.md
team/roles/librarian/reality/host-control/index.md             -> ../security/index.md
team/roles/librarian/reality/agent-mitmproxy/index.md          -> ../infra/index.md
team/roles/librarian/reality/agent-mitmproxy/index.md          -> ../infra/index.md
team/roles/librarian/reality/agent-mitmproxy/index.md          -> ../qa/index.md
team/roles/librarian/reality/_archive/v0.1.31/06__sp-cli-...   -> ../../../../comms/briefs/v0.1.72__sp-cli-fastapi-duality.md
team/roles/librarian/reality/playwright-service/index.md       -> ../security/index.md
team/roles/librarian/reality/playwright-service/index.md       -> ../infra/index.md
team/roles/librarian/reality/playwright-service/index.md       -> ../qa/index.md
team/roles/librarian/reality/vault/index.md                    -> ../security/index.md
team/roles/librarian/reality/vault/proposed/index.md           -> ../cli/aws-dns.md
team/roles/librarian/reality/cli/index.md                      -> ../lets/index.md
team/roles/librarian/reality/cli/index.md                      -> ../lets/index.md
team/roles/librarian/reality/cli/proposed/index.md             -> ../sg-compute/index.md
```

Most are forward references to domains that have not yet migrated (`infra/`, `security/`, `qa/`, `lets/`) — they will resolve once `M-003` completes the remaining 4 domains. Two are genuine fixups: the `host-control` link to a brief that was moved or renamed, and the `vault/proposed` link to a CLI sub-page (`aws-dns.md`) that doesn't exist at that path.

---

## Last Reality Update

From `team/roles/librarian/reality/changelog.md` (most-recent entry on top):

- **2026-05-16** — `sg-compute/index.md` UPDATED for `sg aws billing` CLI sub-package (v0.2.22). Previous: 2026-05-15 (`sg aws dns + acm` — P0+P1+P1.5+ergonomics shipped).

The 2026-05-17 vault-publish landing (v0.2.23) is reflected in `team/roles/librarian/reality/sg-compute/index.md`'s history table but not yet as its own changelog entry — flag for next-session backfill.

---

## Notes for Next Findings Refresh

- The reality master `index.md` header is stale (claims 1 domain migrated; actual is 7). Refresh in concert with the next M-003 batch.
- `open_design/cli/__init__.py` and `neko/cli/__init__.py` should be added to `INC-003` (alongside the existing `firefox/cli/__init__.py` entry).
- Routes catalogue surfaced a 612-line `Routes__Index.py` — confirm whether the static-site HTML belongs in a route handler or should be lifted into a template/static asset.
- The CLAUDE.md endpoint count ("25") vs. wired-route count (23) needs reconciliation — see `service.md` VERIFY note.
- The reality changelog should add a 2026-05-17 entry for `vault-publish` v0.2.23 and a 2026-05-17 entry for this catalogue refresh.
