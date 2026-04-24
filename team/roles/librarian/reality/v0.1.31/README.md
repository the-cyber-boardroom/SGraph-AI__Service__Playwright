# Reality — v0.1.31 (+ agent_mitmproxy v0.1.32 sibling) — 2026-04-20

**Source of truth for what exists today.** Agents must update the relevant file in this folder whenever code changes.

> **Canonical location:** `team/roles/librarian/reality/v0.1.31/`. Earlier `v0.1.29__what-exists-today.md` single-file doc is superseded and kept only until the next Librarian pass removes it.

The reality doc was split into per-concern files this cycle (previously a single ~170-line file). Split reasons: easier to edit one section without re-reading the whole thing; lets the new `agent_mitmproxy/` sibling have its own file without bloating the Playwright surface doc; natural boundary for what each role touches (Architect → schemas, QA → tests, DevOps → docker/CI).

---

## Index

1. [`01__playwright-service.md`](01__playwright-service.md) — Playwright service surface: public + admin endpoints, service classes, schemas, consts.
2. [`02__agent-mitmproxy-sibling.md`](02__agent-mitmproxy-sibling.md) — **NEW in v0.1.32.** Sibling package at repo root (`agent_mitmproxy/`). Admin FastAPI, mitmweb addons, Docker image + ECR helpers, EC2 spin-up script.
3. [`03__docker-and-ci.md`](03__docker-and-ci.md) — Docker images + CI workflows (Playwright + mitmproxy).
4. [`04__tests.md`](04__tests.md) — Unit / integration / deploy test inventory by area.
5. [`05__proposed.md`](05__proposed.md) — What does NOT exist yet (aspirations, deferred work).
6. [`06__sp-cli-duality-refactor.md`](06__sp-cli-duality-refactor.md) — **NEW.** First slices of the `sgraph_ai_service_playwright__cli/` sibling package: read-only `Observability__Service` (`list_stacks`, `get_stack_info`) + `delete_stack` + schemas + isolated boto3 boundary.
7. [`07__sp-cli-ec2-fastapi.md`](07__sp-cli-ec2-fastapi.md) — **NEW.** EC2 create/info/delete exposed as HTTP routes via `Fast_API__SP__CLI` (stand-alone) + `Ec2__Service` adapter over `scripts/provision_ec2.py` + Lambda handler.
8. [`08__sp-cli-lambda-deploy.md`](08__sp-cli-lambda-deploy.md) — **NEW.** Deploys the SP CLI app as its own AWS Lambda: dedicated IAM role (ARN-scoped PassRole), minimal Python 3.12 image (no Chromium), ECR repo, Function URL.
9. [`09__sp-cli-observability-routes.md`](09__sp-cli-observability-routes.md) — **NEW.** Observability list/get/delete mounted as HTTP routes on the same `Fast_API__SP__CLI` app. Also closes the Type_Safe `ValueError` → HTTP 422 gap via a framework-level exception handler.

---

## Summary

**Phase 1 complete + Phase 2 largely complete + v0.1.13 clean-state milestone + v0.1.23 proxy-auth fix + v0.1.24 stateless-surface refactor + v0.1.29 first-pass agentic refactor + v0.1.31 two-Lambda provisioning + EC2 spike + v0.1.32 agent_mitmproxy sibling package.**

- **Playwright API surface: 18 endpoints** — 10 public + 8 `/admin/*` (unauthenticated, read-only). Unchanged from v0.1.29.
- **Playwright service classes: 10 of 10 live.** Unchanged from v0.1.24.
- **agent_mitmproxy admin API: 6 endpoints** — 2 health + 2 CA + 1 config + 1 UI-proxy. API-key-gated.
- **agent_mitmproxy addons: 2** — `Default_Interceptor` (request-id + timing stamps), `Audit_Log` (NDJSON to stdout).
- **Unit tests: 395 (Playwright, unchanged) + 34 passing + 1 skipped (agent_mitmproxy).**

## Changes since v0.1.29

### Playwright (v0.1.30 → v0.1.31)
- `scripts/provision_ec2.py` — throwaway EC2 spike to reproduce the Firefox/WebKit-on-Lambda hang. t3.large AL2023, UserData installs Docker + pulls the ECR image + runs with `FAST_API__AUTH__API_KEY__*` + `SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000`. Idempotent IAM role + SG; `--terminate` to tear down. Tests under `tests/unit/scripts/test_provision_ec2.py`.
- IAM role `sg-playwright-ec2-spike` gained `AmazonSSMManagedInstanceCore` (drop into a shell via `aws ssm start-session`; no SSH).
- SG name corrected (`sg-` prefix dropped — AWS reserves `sg-*` for SG IDs).
- SG description stripped of the em dash (AWS rejects non-ASCII `GroupDescription`).
- `scripts/provision_lambdas.py` — two-Lambda provisioning (`sg-playwright-baseline-<stage>` + `sg-playwright-<stage>`) with `--mode={full, code-only}`. `code-only` skips the ~30–60 s image-pull wait on Python-only refreshes.
- `ci-pipeline.yml::detect-changes` narrowed to `sgraph_ai_service_playwright/docker/images/**` (was `docker/**`); touching deploy-time `Build__Docker__*` helpers no longer forces an image rebuild.
- `ci-pipeline.yml::provision-lambdas` job replaces the old `deploy-code` single-track mode; picks `full` vs `code-only` from the `build-and-push-image` result.

### Sibling package (v0.1.32 — new)
See [`02__agent-mitmproxy-sibling.md`](02__agent-mitmproxy-sibling.md).

---

## Changes: v0.1.46 observability slice (2026-04-20)

### Playwright service
- `metrics/Metrics__Collector.py` — module-level `CollectorRegistry` with 6 `prometheus_client` metrics: `sg_playwright_request_total`, `sg_playwright_request_duration_seconds`, `sg_playwright_chromium_launch_seconds`, `sg_playwright_navigate_seconds`, `sg_playwright_chromium_teardown_seconds`, `sg_playwright_total_duration_seconds`.
- `fast_api/routes/Routes__Metrics.py` — `GET /metrics` API-key-gated Prometheus text exposition.
- `fast_api/Fast_API__Playwright__Service.py` — `setup_routes()` now wires `Routes__Metrics`.
- `service/Playwright__Service.py` — `run_one_shot()` and `browser_screenshot()` record metrics into `Metrics__Collector`.
- `prometheus-client` added to `pyproject.toml` + Docker requirements.

### agent_mitmproxy
- `addons/prometheus_metrics_addon.py` — duck-typed `Prometheus_Metrics` addon; 4 `sg_mitmproxy_*` metrics in `MITMPROXY_REGISTRY`.
- `addons/addon_registry.py` — now includes `metrics_addons`.
- `fast_api/routes/Routes__Metrics.py` — `GET /metrics` API-key-gated Prometheus text exposition.
- `fast_api/Fast_API__Agent_Mitmproxy.py` — wires `Routes__Metrics`.
- `prometheus-client` added to `agent_mitmproxy/requirements.txt`.

### EC2 observability stack (scripts/provision_ec2.py)
- `COMPOSE_YAML_TEMPLATE` extended with 8 new services: `prometheus`, `grafana`, `cadvisor`, `node-exporter`, `loki`, `promtail`, `cloudwatch-agent`, `xray-daemon`. Named volumes: `prometheus_data`, `grafana_data`, `loki_data`.
- Config string constants: `PROMETHEUS_YML`, `LOKI_YML`, `PROMTAIL_YML`, `CLOUDWATCH_AGENT_JSON`, `GRAFANA_DATASOURCES_YAML`, `GRAFANA_DASHBOARDS_YAML`.
- `render_observability_configs_section()` — builds multi-heredoc bash section writing config files to `/opt/sg-playwright/config/`.
- `render_user_data()` now accepts optional `api_key_value=''` (backward-compatible); embeds observability config section.
- `AMI_USER_DATA_TEMPLATE` updated with observability section.
- New IAM constants: `IAM__CLOUDWATCH_POLICY_ARN`, `IAM__XRAY_POLICY_ARN`, `IAM__PROMETHEUS_RW_POLICY_ARN`, `IAM__OBSERVABILITY_POLICY_ARNS`.
- `ensure_instance_profile()` now attaches both `IAM__POLICY_ARNS` and `IAM__OBSERVABILITY_POLICY_ARNS`.
- New CLI commands: `forward-grafana`, `forward-prometheus`, `metrics`. Updated `cmd_smoke()` to show Grafana + Prometheus access hints.
- 4 Grafana dashboard JSON files: playwright request performance, container resources, mitmproxy traffic, system logs.
- AWS account setup runbook: `library/docs/ops/v0.1.33__aws-observability-setup.md`.

---

## Naming Convention

- Historical single-file reality docs: `v{version}__what-exists-today.md` (superseded from v0.1.31 onward).
- Split reality docs: `v{version}/{NN}__{slice}.md` under `team/roles/librarian/reality/`.
- The folder's `README.md` is the index.
