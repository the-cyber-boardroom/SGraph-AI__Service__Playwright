---
title: "Catalogue — CLI"
file: cli.md
shard: cli
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — CLI

The CLI is a Typer hierarchy rooted at a single entry-point class. The `sg` command (with aliases `sgc`, `sg-compute`, and legacy `sp`) aggregates a per-spec sub-typer for every spec under `sg_compute_specs/` plus a handful of cross-cutting verbs (`aws`, `catalog`, `doctor`, `nodes`, `repl`, `observability`).

- **Aggregator:** `sg_compute/cli/Cli__SG.py` — pure `app.add_typer(...)` wiring, no inline command logic.
- **Console-script aliases (`pyproject.toml`):** `sg`, `sgc`, `sg-compute`, `sp` (legacy) — all point at `sg_compute.cli.Cli__SG:app`.
- **Hidden short aliases:** `el`, `os`, `pw`, `ff`, `nk`, `lc`, `ol`, `od`, `lx`, `prom`, `va`, `vp`, `dk`, `ob`.

---

## Top-Level Namespaces

| Namespace | Source typer | Notes |
|-----------|--------------|-------|
| `sg aws` | `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` | AWS resource management. Sub-apps: `dns`, `acm`, `billing`, `cf`, `lambda`. |
| `sg catalog` | `scripts/catalog.py` | List stack types or live stacks across all specs. |
| `sg docker` (alias `sg dk`) | `scripts/docker_stack.py` | Ephemeral Docker EC2 stacks (AL2023 + Docker CE). |
| `sg doctor` | `scripts/doctor.py` | Preflight checks — AWS account / region / ECR / IAM. |
| `sg elastic` (alias `sg el`) | `scripts/elastic.py` | Ephemeral Elasticsearch + Kibana EC2 stacks (legacy script path, not yet migrated into `sg_compute_specs/elastic/`). |
| `sg firefox` (alias `sg ff`) | `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` | Firefox (noVNC + mitmproxy) EC2 stacks. VERIFY: `__init__.py` is 552 LOC — violates CLAUDE.md rule #22 (tracked as `INC-003`). |
| `sg local-claude` (alias `sg lc`) | `sg_compute_specs/local_claude/cli/Cli__Local_Claude.py` | Laptop-local Claude → Ollama via LiteLLM sidecar. |
| `sg neko` (alias `sg nk`) | `sgraph_ai_service_playwright__cli/neko/cli/__init__.py` | Neko (WebRTC browser) EC2 stacks. |
| `sg nodes` | `sg_compute/cli/Cli__Compute__Node.py` | List or delete compute nodes across all specs. |
| `sg ollama` (alias `sg ol`) | `sg_compute_specs/ollama/cli/Cli__Ollama.py` | Ollama GPU EC2 stacks (first spec on `Spec__CLI__Builder`, v0.2.7). |
| `sg open-design` (alias `sg od`) | `sg_compute_specs/open_design/cli/__init__.py` | Open Design EC2 stacks. |
| `sg opensearch` (alias `sg os`) | `scripts/opensearch.py` | OpenSearch + Dashboards EC2 stacks (legacy script path). |
| `sg playwright` (alias `sg pw`) | `sg_compute_specs/playwright/cli/Cli__Playwright.py` | Playwright EC2 stacks. |
| `sg podman` (alias `sg lx`) | `scripts/podman.py` | Podman EC2 stacks (AL2023, SSM). |
| `sg prometheus` (alias `sg prom`) | `scripts/prometheus.py` | Prometheus + cAdvisor EC2 stacks. |
| `sg vault-app` (alias `sg va`) | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py` | Vault App EC2 stacks. VERIFY: file is 790 LOC. |
| `sg vault-publish` (alias `sg vp`) | `sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py` | Subdomain routing for vault-app stacks (v0.2.23). |
| `sg vnc` | `scripts/vnc.py` | VNC stacks (chromium + nginx + mitmproxy). |
| `sg observability` (hidden, alias `sg ob`) | `scripts/observability.py` | AMP + OpenSearch + Grafana read/delete. |
| `sg repl` | `sg_compute/cli/Cli__SG__Repl.py` (`run_repl(app)`) | Interactive shell with prefix matching + arbitrary-depth navigation. |

> Notable: several namespaces are still served by `scripts/*.py` rather than by per-spec `cli/Cli__*.py`. This is the partially-migrated state called out in the ontology proposal (§1.7).

---

## `sg aws` Sub-Apps

| Verb-prefix | File | Key commands |
|-------------|------|--------------|
| `sg aws dns` | `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py` (1,248 LOC — `INC-003`) | `zones list`, `zone show/list/check/purge`, `records add/update/delete/check/get/list`, `instance create-record` |
| `sg aws acm` | `sgraph_ai_service_playwright__cli/aws/acm/cli/Cli__Acm.py` | `list`, `show` |
| `sg aws billing` | `sgraph_ai_service_playwright__cli/aws/billing/cli/Cli__Billing.py` | `last-48h`, `week`, `mtd`, `window`, `summary`, `chart` (v0.2.22) |
| `sg aws cf` | `sgraph_ai_service_playwright__cli/aws/cf/cli/Cli__Cf.py` | CloudFront distribution CRUD (v0.2.23) |
| `sg aws lambda` | `sgraph_ai_service_playwright__cli/aws/lambda_/cli/Cli__Lambda.py` | Lambda deploy + Function URL CRUD (v0.2.23) |

DNS default mode is zero-cache-pollution (authoritative-NS direct via `dig @ns +norecurse`); cache-polluting modes are opt-in behind verbatim WARNING banners. `zone check` cross-references ACM cert validation CNAMEs to identify orphaned records; `zone purge` batch-deletes in a single Route 53 ChangeBatch. See [`team/roles/librarian/reality/_archive/v0.1.31/16__sg-aws-dns-and-acm.md`](../../team/roles/librarian/reality/_archive/v0.1.31/16__sg-aws-dns-and-acm.md) for full surface.

---

## `sg_compute/cli/` — Cross-Cutting CLI

| File | Purpose |
|------|---------|
| `Cli__SG.py` | Top-level aggregator (this file owns the wiring shown above). |
| `Cli__Compute.py` | Pre-aggregator surface for `sg compute …` style verbs (VERIFY: usage relative to `Cli__SG.py`). |
| `Cli__Compute__Node.py` | Cross-spec node operations (`sg nodes`). |
| `Cli__Compute__Pod.py` | Cross-spec pod operations. |
| `Cli__Compute__Spec.py` | Spec discovery commands. |
| `Cli__Compute__Stack.py` | Cross-spec stack operations. |
| `Cli__SG__Repl.py` | Interactive REPL (`run_repl(app)`). |
| `Renderers.py` | Shared output renderers. |
| `Spec__CLI__Loader.py` | Dynamic loader for spec CLIs. |

---

## `Spec__CLI__Builder` Contract (v0.2.6, `sg_compute/cli/base/`)

The per-spec CLI factory adopted in v0.2.6. Every newly authored spec CLI extends `Spec__Service__Base` and consumes `Spec__CLI__Builder` to generate the standard `create/list/info/delete/wait` verb set, leaving the spec to declare only its extras.

| File | Role |
|------|------|
| `Spec__CLI__Builder.py` | Factory — generates a typer app from a `Schema__Spec__CLI__Spec`. |
| `Spec__CLI__Resolver.py` | Resolves spec-specific verb implementations. |
| `Spec__CLI__Errors.py` | Shared error classes for spec CLIs. |
| `Spec__CLI__Defaults.py` | Default parameter values (region, instance type, …). |
| `Spec__CLI__Renderers__Base.py` | Base renderer class (subclassed per spec). |
| `Schema__Spec__CLI__Spec.py` | Typed spec describing a spec's CLI surface. |
| `schemas/Schema__CLI__Exec__Result.py` | Result schema for CLI command execution. |
| `schemas/Schema__CLI__Health__Probe.py` | Health probe result schema. |

Contract doc (Architect): [`library/docs/specs/v0.2.6__authoring-a-new-top-level-spec.md`](../docs/specs/v0.2.6__authoring-a-new-top-level-spec.md).

---

## `sgraph_ai_service_playwright__cli/` — Legacy SP CLI Sub-Packages

Sibling sub-packages that pre-date the `sg_compute_specs/` migration. Each follows the same internal layout (`enums/`, `primitives/`, `schemas/`, `collections/`, `service/`, optionally `cli/`, `fast_api/`).

| Sub-package | Path | Role |
|-------------|------|------|
| `aws/` | `aws/{dns,acm,billing,cf,lambda_}/` | AWS sub-tools (see table above) |
| `catalog/` | `catalog/` | Catalogue service + HTTP routes |
| `core/` | `core/{event_bus,plugin}/` | Cross-cutting event-bus + plugin primitives |
| `docker/` | `docker/` | Docker stack CLI + FastAPI routes |
| `ec2/` | `ec2/` | EC2 instance lifecycle (still consumed by Playwright + sidecar provisioning) |
| `elastic/` | `elastic/{service,lets/cf/{inventory,events,consolidate,sg_send},lets/runs}` | Elasticsearch + Kibana stack management + LETS pipeline (4 slices) |
| `fast_api/` | `fast_api/` | Stand-alone `Fast_API__SP__CLI` (now mounted at `/legacy` under `Fast_API__Compute`, per BV2.10) |
| `firefox/` | `firefox/` | Firefox stack CLI |
| `image/` | `image/` | Shared Docker image build service |
| `neko/` | `neko/` | Neko stack CLI |
| `observability/` | `observability/` | AMP / OpenSearch / Grafana read+delete |
| `opensearch/` | `opensearch/` | OpenSearch stack lifecycle |
| `podman/` | `podman/` | Podman stack lifecycle |
| `prometheus/` | `prometheus/` | Prometheus stack foundation |
| `vault/` | `vault/` | Vault primitives + plugin writers (pre-`sg_compute/vault/` shim) |
| `vnc/` | `vnc/` | VNC stack lifecycle |

The plan-of-record (per BV2.10/BV2.11/BV2.12 history) is to migrate these into `sg_compute_specs/` over time; until that lands, both layouts coexist.

---

## CLI Script Entry Points (`scripts/`)

These still serve as the source of `app: typer.Typer` for several namespaces wired into `Cli__SG.py`:

| Script | Backs which `sg <verb>` |
|--------|-------------------------|
| `scripts/catalog.py` | `sg catalog` |
| `scripts/docker_stack.py` | `sg docker` |
| `scripts/doctor.py` | `sg doctor` |
| `scripts/elastic.py` (1,335 LOC — `INC-003`) | `sg elastic` / `sg el` |
| `scripts/elastic_lets.py` (1,210 LOC — `INC-003`) | `sg el lets cf {inventory,events,consolidate,sg-send}` (mounted by `scripts/elastic.py`) |
| `scripts/observability.py` (609 LOC) | `sg observability` / `sg ob` |
| `scripts/opensearch.py` | `sg opensearch` / `sg os` |
| `scripts/podman.py` | `sg podman` / `sg lx` |
| `scripts/prometheus.py` | `sg prometheus` / `sg prom` |
| `scripts/provision_ec2.py` (2,510 LOC — `INC-003`) | Direct EC2 provisioner (not via `Cli__SG.py`) |
| `scripts/sg_compute_cli.py` | VERIFY: usage |
| `scripts/run_sp_cli.py` | Legacy SP CLI entry (now subsumed by `Fast_API__Compute` per BV2.10). |
| `scripts/sp-cli__run-locally.sh` | Shell convenience wrapper. |
| `scripts/vnc.py` | `sg vnc` |

---

## Cross-Links

- Spec inventory + status: [`specs.md`](specs.md)
- Tests: [`tests.md`](tests.md) (esp. `sg_compute__tests/cli/` + `tests/unit/sgraph_ai_service_playwright__cli/`)
- Authoring contract: [`library/docs/specs/v0.2.6__authoring-a-new-top-level-spec.md`](../docs/specs/v0.2.6__authoring-a-new-top-level-spec.md)
- Reality (CLI surface): currently in [`team/roles/librarian/reality/sg-compute/cli.md`](../../team/roles/librarian/reality/sg-compute/cli.md). Legacy SP CLI shim: [`team/roles/librarian/reality/_archive/v0.1.31/06__sp-cli-duality-refactor.md`](../../team/roles/librarian/reality/_archive/v0.1.31/06__sp-cli-duality-refactor.md).
