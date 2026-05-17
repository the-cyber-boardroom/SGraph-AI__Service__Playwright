# cli — Reality Index

**Domain:** `cli/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/06,07,08,09,13,16__*.md`.

The `sp` / `sg` / `ob` typer CLI surface and its FastAPI duality (`Fast_API__SP__CLI`). Covers `sgraph_ai_service_playwright__cli/` (the new top-level package born of the v0.1.72 duality refactor) plus the `scripts/*.py` Typer entry points.

**Canonical package:** `sgraph_ai_service_playwright__cli/`. Sibling of `sgraph_ai_service_playwright/` and (former) `agent_mitmproxy/`. Houses the Type_Safe refactor of the `sp` / `ob` CLI and the FastAPI app that mounts the same operations as HTTP routes.

**Companion FastAPI app:** `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` — stand-alone `osbot_fast_api.api.Fast_API` subclass. Deployed as its own Lambda (`sp-playwright-cli-{stage}`) with its own IAM role, ECR repo, and Function URL.

> **Post-v0.1.31 note:** BV2.10 (2026-05-05) mounted `Fast_API__SP__CLI` as a sub-app at `/legacy` on `Fast_API__Compute`, with an ASGI wrapper injecting `X-Deprecated: true`. v0.2.22 added the `sg aws billing` family; v0.2.23 added the `sg aws cf` + `sg aws lambda` + vault-publish CLIs. See [`sg-compute/index.md`](../sg-compute/index.md) for those additions.

---

## EXISTS — sub-page map

The CLI surface is large; per the 300-line fractal rule it is split into focused sub-files. The summary table here points at where each area is documented.

| Sub-file | Covers |
|----------|--------|
| [`duality.md`](duality.md) | The v0.1.72 duality refactor — new `__cli/` package, `aws/Stack__Naming`, `Ec2__AWS__Client`, `image/Image__Build__Service`, the per-section sister tree (`elastic / opensearch / prometheus / vnc`), Phase C strip + Phase D command cleanup |
| [`ec2.md`](ec2.md) | The EC2 FastAPI routes slice (`Fast_API__SP__CLI` + `Routes__Ec2__Playwright`), schemas, type-safe-validation handler, deploy slice (IAM role `sp-playwright-cli-lambda`, image, Lambda settings, CI workflow) |
| [`observability.md`](observability.md) | The observability sub-package (Type_Safe primitives / enums / schemas / `Observability__AWS__Client` / `Observability__Service`) + `Routes__Observability` HTTP surface + the `Routes__Linux__Stack` / `Routes__Docker__Stack` / `Routes__Elastic__Stack` / `Routes__Stack__Catalog` / `Routes__Vnc__Stack` mounts |
| [`aws-dns.md`](aws-dns.md) | The 2026-05-15 `sg aws dns` + `sg aws acm` slice — Route 53 management, ACM inventory, smart-verify, `zone check` classification |

---

## Quick reference — Top-level Typer commands

This is the high-level surface; details live in the sub-files.

### `sp` / `sg` (compute + ops)

| Command | Group | Where documented |
|---------|-------|------------------|
| `sp create / list / info / delete` (Playwright EC2) | `ec2` | [`ec2.md`](ec2.md) |
| `sp el ...` (Elastic stacks + LETS pipelines) | `elastic` | [`duality.md`](duality.md), [`lets/index.md`](../lets/index.md) |
| `sp os ...` (OpenSearch stacks) | `opensearch` | [`duality.md`](duality.md) |
| `sp prom ...` (Prometheus stacks + metrics) | `prometheus` | [`duality.md`](duality.md) |
| `sp vnc ...` (KasmVNC + mitmproxy + nginx stacks) | `vnc` | [`duality.md`](duality.md) |
| `sp linux ...` / `sp docker ...` | `linux/docker` | [`observability.md`](observability.md) |
| `sp vault ...` (subgroup, post Phase D) | `vault` | [`vault/index.md`](../vault/index.md) |
| `sp ami ...` (subgroup, post Phase D) | `ami` | [`duality.md`](duality.md) — Phase D section |
| `ob list / get / delete` (legacy observability stack) | `observability` | [`observability.md`](observability.md) |
| `sg aws dns ...` / `sg aws acm ...` | `aws` | [`aws-dns.md`](aws-dns.md) |
| `sg aws billing ...` (v0.2.22) | `aws/billing` | [`sg-compute/index.md`](../sg-compute/index.md) |
| `sg aws cf ...` / `sg aws lambda ...` (v0.2.23) | `aws` | [`sg-compute/index.md`](../sg-compute/index.md) |
| `sg vp ...` (vault-publish slug bootstrap, v0.2.23) | `vp` | [`sg-compute/index.md`](../sg-compute/index.md) |

### `Fast_API__SP__CLI` route count (at v0.1.31 freeze)

| Slice | Endpoint count delta | Total |
|-------|---------------------|-------|
| PR-0 (EC2 + observability mounts) | +10 | 10 |
| PR-1 (linux + docker mounts, slice 13) | +10 | 20 |
| PR-2 (catalog mount, slice 13) | +2 | 22 |
| PR-3 (elastic mount, slice 13) | +5 | 27 |
| Slice 14 (VNC stack + flows) | +6 | **33** |

OpenSearch + Prometheus route classes exist in code but are not mounted on `Fast_API__SP__CLI` as of v0.1.31 — see PROPOSED.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources: [`_archive/v0.1.31/06__sp-cli-duality-refactor.md`](../_archive/v0.1.31/06__sp-cli-duality-refactor.md), [`07__sp-cli-ec2-fastapi.md`](../_archive/v0.1.31/07__sp-cli-ec2-fastapi.md), [`08__sp-cli-lambda-deploy.md`](../_archive/v0.1.31/08__sp-cli-lambda-deploy.md), [`09__sp-cli-observability-routes.md`](../_archive/v0.1.31/09__sp-cli-observability-routes.md), [`13__sp-cli-linux-docker-elastic-catalog-ui.md`](../_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md), [`16__sg-aws-dns-and-acm.md`](../_archive/v0.1.31/16__sg-aws-dns-and-acm.md)
- LETS pipelines triggered from `sp el lets cf ...`: [`lets/index.md`](../lets/index.md)
- UI dashboard consuming `Fast_API__SP__CLI`: [`ui/index.md`](../ui/index.md)
- Vault primitives + writer: [`vault/index.md`](../vault/index.md)
- Successor surface: [`sg-compute/index.md`](../sg-compute/index.md) — `Fast_API__Compute` mounts `Fast_API__SP__CLI` at `/legacy`
