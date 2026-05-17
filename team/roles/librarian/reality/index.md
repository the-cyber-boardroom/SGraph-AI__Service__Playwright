# Reality — Master Index

**Version:** v0.2.25 | **Last updated:** 2026-05-17 | **Maintained by:** Librarian (daily run)
**Structure:** Domain tree — each domain has its own directory with `index.md` and `proposed/`

This file is the entry point. Read it to find the right domain, then go to that domain's `index.md` for EXISTS details and `proposed/index.md` for PROPOSED items.

**Rule:** If a feature is not listed in a domain index, it does not exist. Proposed features are labelled `PROPOSED — does not exist yet.` Claimed features that are not in any index DO NOT EXIST.

---

## Why this file exists (read once)

This `index.md` replaces the version-stamped reality monoliths (`v0.1.13__what-exists-today.md`, …, `v0.1.31/`). Those files were a snapshot per release; the domain tree is a living surface that evolves in place.

- **Domain index** — current state for one domain. Stable filename, content evolves.
- **Domain `proposed/index.md`** — what is wanted but not built, scoped to that domain.
- **`changelog.md`** — pointer log: date \| domain(s) updated \| one-liner. The time series.
- **Old monoliths** — preserved for historical reference (`v0.1.31/` is the most recent), no longer authoritative.

When code lands, the author updates the relevant domain's `index.md` in the same commit. The Librarian verifies, fills gaps, and splits files when they exceed ~300 lines.

---

## Domain Map

| Domain | Directory | What it covers | Status |
|--------|-----------|----------------|--------|
| **Playwright service** | [`playwright-service/`](playwright-service/index.md) | Core FastAPI service, routes, schemas, Step__Executor, Browser__Launcher, capability profiles | ✅ MIGRATED |
| **agent_mitmproxy** | [`agent-mitmproxy/`](agent-mitmproxy/index.md) | Sibling package (mitmproxy admin FastAPI, addons, reverse-proxied UI) | ✅ MIGRATED |
| **CLI** | [`cli/`](cli/index.md) | `sp-cli` Typer command + `Fast_API__SP__CLI` (the duality) — observability, EC2, catalog, vault, lets | ✅ MIGRATED (split: `duality.md` / `ec2.md` / `observability.md` / `aws-dns.md`) |
| **Host Control Plane** | [`host-control/`](host-control/index.md) | `sgraph_ai_service_playwright__host` package — container runtime abstraction, shell executor, Routes__Host__* | ✅ MIGRATED (pilot) |
| **UI** | [`ui/`](ui/index.md) | Static-site dashboard — `sp-cli-*` web component family, plugins, fractal-UI rebuild | ✅ MIGRATED |
| **Vault** | [`vault/`](vault/index.md) | Vault primitives, `Vault__Spec__Writer` (formerly `Vault__Plugin__Writer`), per-spec namespaced writes | ✅ MIGRATED |
| **LETS** | [`lets/`](lets/index.md) | Log Event Tracking System: CF inventory + events + consolidate slices | ✅ MIGRATED |
| **Infra** | [`infra/`](infra/index.md) | Docker images, CI/CD, ECR, Lambda deploy, EC2 provisioning, observability stack | ✅ MIGRATED |
| **QA** | [`qa/`](qa/index.md) | Tests (unit, integration, deploy-via-pytest), smoke tests, test inventory | ✅ MIGRATED |
| **Security** | [`security/`](security/index.md) | JS expression allowlist, vault-key hygiene, security-group naming, AppSec rules | ✅ MIGRATED |
| **SG/Compute** | [`sg-compute/`](sg-compute/index.md) | `sg_compute` SDK + `sg_compute_specs` catalogue — ephemeral EC2 nodes, spec contract, helpers layer | ✅ MIGRATED |

Each domain directory contains:

- `index.md` — EXISTS items + PROPOSED summary + links to sub-files
- `proposed/index.md` — full list of proposed features for this domain
- Sub-files when `index.md` exceeds ~300 lines (fractal split rule)

---

## Status (as of 2026-05-17)

| Metric | Value |
|--------|-------|
| Code version | v0.2.25 |
| Domains in master map | 11 |
| Domains migrated to new format | **11 of 11** |
| Old version-stamped monoliths archived | 4 (`v0.1.13`, `v0.1.24`, `v0.1.29`, plus `v0.1.31/` directory) |

Cross-cutting proposed items from `_archive/v0.1.31/05__proposed.md` are distributed across the per-domain `proposed/index.md` files. Each domain's `proposed/` uses `P-N` IDs scoped to that domain.

---

## See also

- [`README.md`](README.md) — rules, structure, lifecycle
- [`changelog.md`](changelog.md) — pointer log of every reality update
- [`../DAILY_RUN.md`](../DAILY_RUN.md) — Librarian routine + backlog (the migration queue)
- [`../ROLE.md`](../ROLE.md) — Librarian role definition
- [`../activity-log.md`](../activity-log.md) — session continuity
