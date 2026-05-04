# 01 — Project Overview

→ [Catalogue README](README.md)

---

## What This Project Is

A browser-automation API + cloud control plane + log analytics pipeline.

- **Playwright service** (`sgraph_ai_service_playwright/`) — FastAPI app that exposes
  browser actions (navigate, click, fill, screenshot, sequences) over HTTP. Runs on
  Lambda (via Lambda Web Adapter), EC2, Docker, local. One Docker image for all targets.
- **SP CLI / control plane** (`sgraph_ai_service_playwright__cli/`) — Type_Safe refactor
  of all ephemeral-stack management: EC2 instances, Elastic/Kibana stacks, OpenSearch
  stacks, Prometheus stacks, and the LETS CloudFront log pipeline. Exposed as both a
  Typer CLI and a stand-alone FastAPI Lambda.
- **agent_mitmproxy** (`agent_mitmproxy/`) — sidecar forward-proxy (mitmproxy + FastAPI
  admin). Runs alongside the Playwright service on EC2.

---

## Two Main Packages

| Package | Path | Description |
|---------|------|-------------|
| `sgraph_ai_service_playwright` | `sgraph_ai_service_playwright/` | Browser automation FastAPI service |
| `sgraph_ai_service_playwright__cli` | `sgraph_ai_service_playwright__cli/` | Stack control-plane CLI + API |

Sub-packages under `__cli/`:

| Sub-package | Path suffix | Concern |
|-------------|-------------|---------|
| `aws/` | `aws/` | Shared naming helpers (`Stack__Naming`) |
| `deploy/` | `deploy/` | SP CLI Lambda image + IAM role provisioning |
| `ec2/` | `ec2/` | EC2 instance lifecycle (Playwright + sidecar stack) |
| `elastic/` | `elastic/` | Elastic/Kibana ephemeral stack + LETS pipeline |
| `image/` | `image/` | Shared Docker image build service |
| `observability/` | `observability/` | AMP + OpenSearch + Grafana stack read/delete |
| `opensearch/` | `opensearch/` | Ephemeral OpenSearch + Dashboards EC2 stacks |
| `prometheus/` | `prometheus/` | Prometheus EC2 stack (foundation only) |

---

## Stack Snapshot

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 / x86_64 |
| Browser image base | `mcr.microsoft.com/playwright/python:v1.58.0-noble` |
| Lambda adapter | AWS Lambda Web Adapter 1.0.0 |
| Web framework | FastAPI via `osbot-fast-api-serverless` |
| Type system | `Type_Safe` from `osbot-utils` — **never Pydantic, never Literals** |
| AWS operations | `osbot-aws` — **never raw boto3** (narrow documented exceptions only) |
| Browser | Playwright sync API — only `Step__Executor` calls `page.*` |
| CLI | Typer |
| Testing | pytest — **no mocks, no patches** |
| CI/CD | GitHub Actions + deploy-via-pytest |

---

## Non-Negotiable Code Rules

1. Every class extends `Type_Safe` — no plain Python classes
2. No raw primitives as attributes — use `Safe_*` / `Enum__*` / collection subclasses
3. No `Literal` — use `Enum__*` classes
4. One class per file; filename matches class name exactly
5. `__init__.py` files stay empty — callers import from fully-qualified paths
6. Every route returns `.json()` on a `Type_Safe` schema — no raw dicts
7. `═══` 80-char section headers in every file
8. Inline comments only — no docstrings
9. No underscore prefix for "private" methods

See `/.claude/CLAUDE.md` for the full rule set.

---

## Cross-Links

- `library/catalogue/02__cli-packages.md` — CLI sub-package detail
- `library/catalogue/05__playwright-service.md` — FastAPI service detail
- `team/roles/librarian/reality/v0.1.31/README.md` — what exists today
