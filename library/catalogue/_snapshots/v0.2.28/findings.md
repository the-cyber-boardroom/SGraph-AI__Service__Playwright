---
title: "Catalogue — Findings"
file: findings.md
shard: findings
as_of: v0.2.28
last_refreshed: 2026-05-17 (PM sync, post-M-016)
maintainer: Librarian
prior_snapshot: v0.2.25 (commit ab0c380, 2026-05-17 AM)
---

# Catalogue — Findings

Repo-health snapshot — oversized files, broken-link spot-check, migration progress, ID-registry state. Computed against working tree at root commit `759dfaa` (dev tip), branch `claude/setup-librarian-agent-r9azr`. Adopted from the `sgai-tools` pattern (ontology proposal §4.4).

> **Refresh delta vs prior snapshot (v0.2.25):** +101 `.md` files, +532 `.py` files (mostly v0.2.29 `sg aws` slice scaffolding + 8 new spec sub-packs). +11 oversized `.md` files. Reality migration **complete** (11 of 11 domains). Broken-link count: **19 → 0** (M-015 closed).

---

## Markdown — Volume & Health

| Metric | v0.2.25 | v0.2.28 | Δ |
|--------|--------:|--------:|---:|
| Total `.md` files | 724 | **825** | +101 |
| `.md` files > 300 lines | 97 | **108** | +11 |

The 300-line threshold is the fractal-growth rule (CLAUDE.md / `library/guides/v0.2.15__markdown_doc_style.md`). The +11 growth came from the v0.2.29 dev_pack (`library/dev_packs/v0.2.29__sg-aws-primitives-expansion/` + 8 sibling packs) and 5 architect reviews under `team/roles/architect/reviews/05/17/`.

### Top 10 oversized markdown files

| Lines | Path | Status |
|------:|------|--------|
| 1,943 | `team/humans/dinis_cruz/claude-code-web/05/15/08/architect__sg-aws-dns__plan.md` | SCRATCH — promote-or-archive candidate |
| 1,455 | `library/guides/v3.28.0__safe_primitives.md` | upstream dev-pack guide |
| 1,286 | `library/guides/v3.1.1__testing_guidance.md` | upstream dev-pack guide |
| 1,167 | `library/docs/specs/v0.20.55__ci-pipeline.md` | M-007d note — banner-fix-only, kept whole |
| 863 | scratch architect review | |
| 859 | `library/guides/v3.63.4__type_safe.md` | upstream |
| 829 | `library/guides/v3.63.3__collections_subclassing.md` | upstream |
| 805 | `library/dev_packs/v0.1.101__mvp-of-admin-and-user-ui/03__ui-design-and-components.md` | historical dev_pack |
| 756 | `library/dev_packs/v0.1.111__ui-refactor-to-use-vault/03__vault-integration.md` | historical dev_pack |
| 750 | `library/docs/specs/v0.2.6__authoring-a-new-top-level-spec.md` | |

The split of `v0.20.55__schema-catalogue-v2.md` (was 1,439) and `__routes-catalogue-v2.md` (was 1,234) drops them off the top 10 — both now ≤ 617 lines per part.

---

## Python — Oversized Files (over 500 LOC)

| Metric | v0.2.25 | v0.2.28 | Δ |
|--------|--------:|--------:|---:|
| Total `.py` files | 2,169 | **2,701** | +532 |

### Top 10

| Lines | Path | Notes |
|------:|------|-------|
| 1,335 | `scripts/elastic.py` | `INC-003` |
| 1,248 | `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py` | `INC-003` |
| 1,210 | `scripts/elastic_lets.py` | `INC-003` |
| 851 | `team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/sg_lab_mvp.py` | SCRATCH-grade — VERIFY whether this should live elsewhere |
| 790 | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` | EXPERIMENTAL spec; trending up |
| 678 | `sgraph_ai_service_playwright__cli/elastic/service/Elastic__Service.py` | |
| 664 | `scripts/observability_opensearch.py` | |
| 635 | `sg_compute_specs/vault_app/service/Vault_App__Service.py` | |
| 612 | `sg_compute_specs/playwright/core/fast_api/routes/Routes__Index.py` | Inlined static-site HTML; lift to template |
| 609 | `scripts/observability.py` | |

> `scripts/provision_ec2.py` (2,510 LOC, top of last snapshot) **no longer in the tree** — refactored or removed in v0.2.29 dev work.

---

## `__init__.py` Rule Violations (CLAUDE.md rule #22)

The rule mandates empty `__init__.py`. Non-empty files found (top 3):

| Lines | Path | INC ref |
|------:|------|---------|
| 552 | `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` | `INC-003` |
| 228 | `sg_compute_specs/open_design/cli/__init__.py` | `INC-003` (added 2026-05-17) |
| 225 | `sgraph_ai_service_playwright__cli/neko/cli/__init__.py` | `INC-003` (added 2026-05-17) |

23 `__init__.py` files contain non-whitespace content (most are <10 lines and below the headline threshold). Full list under M-008's weekly health scan.

---

## Reality Migration Progress

| Metric | v0.2.25 | v0.2.28 |
|--------|--------:|--------:|
| Total domains in master map | 11 | 11 |
| Domains with `{domain}/index.md` | 7 | **11** ✅ |
| Domains with `{domain}/proposed/` | 7 | **11** ✅ |
| Domains still on `_archive/v0.1.31/` shim | 4 | **0** ✅ |
| Archived flat snapshots in `_archive/` | 4 + `v0.1.31/` | 4 + `v0.1.31/` |

Migration **complete**. `cli/` and `sg-compute/` are split into sub-files per the 300-line rule. New domain reality entries authored by Dev under `cli/aws-*.md` (7 sub-files) for the v0.2.29 work-stream.

---

## Open Migration Tasks (`M-NNN` — from `team/roles/librarian/ids/README.md`)

| ID | Title | Status |
|----|-------|--------|
| `M-001a..d` | Phase 1 (CLAUDE.md, README, verified-by, ids registry) | ✅ DONE 2026-05-17 |
| `M-002..M-007d` | Archive + per-domain indexes + onboarding rename + catalogue rewrite + spec splits | ✅ DONE 2026-05-17 |
| `M-008` | Health scan (continuous — broken-link walk, naming-violation report) | weekly cadence — partial via this shard |
| `M-009` | Pointer-log entry per code-affecting commit | ONGOING |
| `M-010` | Refresh `verified-by.md` | ONGOING — last entry 2026-05-17 PM |
| `M-011` | Refresh `catalogue/findings.md` per version bump | ✅ DONE 2026-05-17 PM (this file) |
| `M-012` | Process `library/docs/_to_process/` inbox | ONGOING |
| `M-013` | Reconcile endpoint count (CLAUDE.md said 25; actual 16 direct + admin surface) | ✅ DONE 2026-05-17 PM |
| `M-014` | VERIFY markers in domain indexes (post-BV2.11/BV2.12 reconciliation) | IN PROGRESS — agent dispatched |
| `M-015` | Resolve 19 broken links in reality tree | ✅ DONE 2026-05-17 PM (0 remain) |
| `M-016` | Cut `_snapshots/v0.2.28/` + re-run findings | ✅ DONE 2026-05-17 PM |
| `M-017` | CLAUDE.md rule for INC-004 — Architect confirmation pending | DEFERRED |

---

## Broken-Link Spot-Check (REALITY tree only)

Scope: every `.md` under `team/roles/librarian/reality/`. Relative `[text](path)` links only (http/mailto/anchor-only skipped).

| Metric | v0.2.25 | v0.2.28 |
|--------|--------:|--------:|
| Links checked | 218 | ~240 |
| Broken | 19 | **0** ✅ |

**Resolution path (M-015):** 12 were forward references to `infra/`, `lets/`, `qa/`, `security/` — automatically resolved when M-003 created those domain indexes. 5 were depth-miscalculated relative paths (added missing `..` segment) in `vault/proposed/index.md`, `cli/proposed/index.md`, `host-control/index.md`, `cli/aws-creds.md`, `cli/aws-ec2.md`. 2 were in archived docs (`_archive/v0.1.31/06__sp-cli-duality-refactor.md`) — same depth-miscalc fix applied to the archive.

Repo-wide broken-link walk remains M-008's responsibility (weekly cadence).

---

## Last Reality Update

From `team/roles/librarian/reality/changelog.md` (most-recent entry on top):

- **2026-05-17 PM** — v0.2.29 `sg aws` work-stream landed (Foundation + 8 slices). All 7 `cli/aws-*.md` reality sub-files added by Dev. Librarian intake: changelog block, version stamp bump, INC-004/005 minted.
- **2026-05-17 AM** — M-001..M-007 ontology rollout. Reality tree restructured; 8 live catalogue shards; specs split.

---

## INC Registry (active items)

| INC | One-line | Status |
|---|---|---|
| `INC-001` | `sg-*` GroupName rejected by AWS `CreateSecurityGroup` | CLAUDE.md rule #14 |
| `INC-002` | AWS Name tag double-prefix | CLAUDE.md rule #15 |
| `INC-003` | Oversized Python files + `__init__.py` rule-22 violations (8 files) | Flagged to Dev |
| `INC-004` | v0.2.29 Foundation follow-up `bcd33439` wiped Slice B/C/D CLI bodies (regression) | Recovered in `c4cc6ea0`; rule wording TBD by Architect (M-017) |
| `INC-005` | Direct `boto3` use spread to 6 slices / 9 client files | Flagged to Architect/Dev for `osbot-aws` migration |

---

## Notes for Next Findings Refresh

- M-014 (VERIFY markers in 4 domains) lands when the dispatched agent reports back; refresh this shard at that time.
- Consider lifting `sg_lab_mvp.py` (851 LOC SCRATCH-grade Python in a brief folder) into a proper script location.
- `Routes__Index.py` at 612 LOC still surprising — the static "Try it out" HTML should likely move to a Jinja template or static asset.
- The reality changelog should be re-cross-checked against `team/claude/debriefs/index.md` to ensure every debriefed slice has a pointer entry (M-009).
- `provision_ec2.py` dropping off the oversized list is suspicious — verify it wasn't accidentally removed during v0.2.29 dev work.
