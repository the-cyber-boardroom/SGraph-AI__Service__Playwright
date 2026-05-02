# Reality — Master Index

**Version:** v0.1.140 | **Last updated:** 2026-05-02 | **Maintained by:** Librarian (daily run)
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
| **Playwright service** | [`playwright-service/`](playwright-service/index.md) | Core FastAPI service, routes, schemas, Step__Executor, Browser__Launcher, capability profiles | TBD — migrate from `v0.1.31/01__playwright-service.md` |
| **agent_mitmproxy** | [`agent-mitmproxy/`](agent-mitmproxy/index.md) | Sibling package (mitmproxy admin FastAPI, addons, reverse-proxied UI) | TBD — migrate from `v0.1.31/02__agent-mitmproxy-sibling.md` |
| **CLI** | [`cli/`](cli/index.md) | `sp-cli` Typer command + `Fast_API__SP__CLI` (the duality) — observability, EC2, catalog, vault, lets | TBD — migrate from `v0.1.31/06,07,09__*.md` and `v0.1.31/10,11,12__lets-cf-*.md` |
| **Host Control Plane** | [`host-control/`](host-control/index.md) | `sgraph_ai_service_playwright__host` package — container runtime abstraction, shell executor, Routes__Host__* | DONE — pilot migration (this slice) |
| **UI** | [`ui/`](ui/index.md) | Static-site dashboard — `sp-cli-*` web component family, plugins, fractal-UI rebuild | TBD — migrate from `v0.1.31/13,14,15__*.md` |
| **Vault** | [`vault/`](vault/index.md) | Vault primitives, `Vault__Plugin__Writer`, per-plugin namespaced writes | TBD — seed from recent commits (post-fractal-UI brief 04) |
| **LETS** | [`lets/`](lets/index.md) | Log Event Tracking System: CF inventory + events + consolidate slices | TBD — migrate from `v0.1.31/10,11,12__lets-cf-*.md` |
| **Infra** | [`infra/`](infra/index.md) | Docker images, CI/CD, ECR, Lambda deploy, EC2 provisioning, observability stack | TBD — migrate from `v0.1.31/03__docker-and-ci.md`, `v0.1.31/08__sp-cli-lambda-deploy.md` |
| **QA** | [`qa/`](qa/index.md) | Tests (unit, integration, deploy-via-pytest), smoke tests, test inventory | TBD — migrate from `v0.1.31/04__tests.md` |
| **Security** | [`security/`](security/index.md) | JS expression allowlist, vault-key hygiene, security-group naming, AppSec rules | TBD — extract cross-cutting items from CLAUDE.md and `v0.1.31/01__playwright-service.md` |

Each domain directory contains:

- `index.md` — EXISTS items + PROPOSED summary + links to sub-files
- `proposed/index.md` — full list of proposed features for this domain
- Sub-files when `index.md` exceeds ~300 lines (fractal split rule)

---

## Status (as of 2026-05-02)

| Metric | Value |
|--------|-------|
| Code version | v0.1.140 |
| Domains in master map | 10 |
| Domains migrated to new format | 1 (`host-control/` — pilot) |
| Domains still on v0.1.31 split | 9 |
| Old version-stamped monoliths archived | 4 (`v0.1.13`, `v0.1.24`, `v0.1.29`, plus `v0.1.31/` directory) |

The migration from version-stamped files to the domain tree is staged. See [`team/roles/librarian/DAILY_RUN.md`](../DAILY_RUN.md) backlog for the per-domain queue. Until each domain is migrated, the corresponding `v0.1.31/NN__*.md` file remains the authoritative source for that area.

---

## Migration shim — current sources of truth

| Domain | Authoritative source while migration pending |
|--------|------------------------------------------------|
| Playwright service | [`v0.1.31/01__playwright-service.md`](v0.1.31/01__playwright-service.md) |
| agent_mitmproxy | [`v0.1.31/02__agent-mitmproxy-sibling.md`](v0.1.31/02__agent-mitmproxy-sibling.md) |
| CLI | [`v0.1.31/06__sp-cli-duality-refactor.md`](v0.1.31/06__sp-cli-duality-refactor.md), [`07`](v0.1.31/07__sp-cli-ec2-fastapi.md), [`09`](v0.1.31/09__sp-cli-observability-routes.md), [`13`](v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md) (catalog routes) |
| UI | [`v0.1.31/13`](v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md), [`14`](v0.1.31/14__sp-cli-ui-sg-layout-vnc-wiring.md), [`15`](v0.1.31/15__sp-cli-ui-dev-agent-dashboard.md) |
| LETS | [`v0.1.31/10`](v0.1.31/10__lets-cf-inventory.md), [`11`](v0.1.31/11__lets-cf-events.md), [`12`](v0.1.31/12__lets-cf-consolidate.md) |
| Infra | [`v0.1.31/03__docker-and-ci.md`](v0.1.31/03__docker-and-ci.md), [`v0.1.31/08__sp-cli-lambda-deploy.md`](v0.1.31/08__sp-cli-lambda-deploy.md) |
| QA | [`v0.1.31/04__tests.md`](v0.1.31/04__tests.md) |
| Vault | (no v0.1.31 slice — seed from `sgraph_ai_service_playwright__cli/vault/` and post-fractal-UI brief 04) |
| Security | (cross-cutting — extract from CLAUDE.md rules + `v0.1.31/01__playwright-service.md` allowlist section) |

Cross-cutting proposed surface today lives in [`v0.1.31/05__proposed.md`](v0.1.31/05__proposed.md) — the migration distributes it into per-domain `proposed/index.md` files.

---

## See also

- [`README.md`](README.md) — rules, structure, lifecycle
- [`changelog.md`](changelog.md) — pointer log of every reality update
- [`../DAILY_RUN.md`](../DAILY_RUN.md) — Librarian routine + backlog (the migration queue)
- [`../ROLE.md`](../ROLE.md) — Librarian role definition
- [`../activity-log.md`](../activity-log.md) — session continuity
