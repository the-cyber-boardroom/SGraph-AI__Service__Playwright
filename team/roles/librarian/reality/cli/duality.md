# cli — Duality Refactor + Sister Sections

**Parent:** [`index.md`](index.md) | **Last updated:** 2026-05-17
**Source:** `_archive/v0.1.31/06__sp-cli-duality-refactor.md`.

The v0.1.72 duality refactor: a new `sgraph_ai_service_playwright__cli/` package that houses the Type_Safe port of the `sp` / `ob` CLI plus the FastAPI app that exposes the same operations as HTTP routes. Phase A laid shared foundations; Phase B added sister sections per stack type; Phase C stripped the Playwright EC2; Phase D cleaned up the typer command tree.

---

## EXISTS (code-verified)

### Phase A foundations (2026-04-26)

#### `aws/Stack__Naming` (Phase A step 1)

`aws/Stack__Naming.py` — Type_Safe class binding a `section_prefix` (`elastic`, `opensearch`, `prometheus`, `vnc`, …) once and exposing:

- `aws_name_for_stack()` — Name tag with section prefix; never doubles when the input already carries the prefix.
- `sg_name_for_stack()` — SG GroupName with `-sg` suffix; never starts with reserved `sg-`.

`Elastic__AWS__Client.py` declares `ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')` at module level; future sister sections each get their own `*_NAMING` constant pointing at the same `Stack__Naming` class.

Tests: 9 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py`.

#### `ec2/service/Ec2__AWS__Client` (Phase A steps 3a–3d, 3f)

Central EC2 AWS boundary. Hosts previously-private helpers from `scripts/provision_ec2.py`:

| Surface | Symbol | Form |
|---------|--------|------|
| Pure helpers | `random_deploy_name`, `get_creator`, `uptime_str`, `instance_tag`, `instance_deploy_name` | Functions; no AWS calls |
| Constants | `TAG__SERVICE_KEY`, `TAG__SERVICE_VALUE`, `TAG__DEPLOY_NAME_KEY`, `INSTANCE_STATES_LIVE` | Tag/state values |
| Type_Safe class | `Ec2__AWS__Client` | `ec2()` (test seam); `find_instances()`; `find_instance_ids()`; `resolve_instance_id(target)`; `terminate_instances(nickname)` |
| AWS context (3b) | `aws_account_id`, `aws_region`, `ecr_registry_host`, `default_playwright_image_uri`, `default_sidecar_image_uri` | Module-level functions over `osbot_aws.AWS_Config` |
| IAM (3c) | `IAM__ROLE_NAME`, `IAM__*_POLICY_ARN(S)`, `IAM__ASSUME_ROLE_SERVICE`, `IAM__PASSROLE_POLICY_NAME`; `decode_aws_auth_error(exc)`, `ensure_caller_passrole(account)`, `ensure_instance_profile()` | Module-level |
| SG + AMI (3d) | `SG__NAME`, `SG__DESCRIPTION`, `EC2__AMI_OWNER_AMAZON`, `EC2__AMI_NAME_AL2023`, `EC2__PLAYWRIGHT_PORT`, `EC2__SIDECAR_ADMIN_PORT`, `EC2__BROWSER_INTERNAL_PORT`, `SG_INGRESS_PORTS`, `TAG__AMI_STATUS_KEY` | Module-level. `SG__DESCRIPTION` is ASCII-only (AWS rejects multi-byte). |
| SG + AMI methods (3d) | `Ec2__AWS__Client.ensure_security_group()`, `latest_al2023_ami_id()`, `create_ami(instance_id, name)`, `wait_ami_available(ami_id, timeout=900)`, `tag_ami(ami_id, status)`, `latest_healthy_ami()` | All go through `self.ec2()` |

In step 3f, three typer commands (`cmd_list`, `cmd_info`, `cmd_delete`) reduced to thin wrappers over `Ec2__Service`:

- `Schema__Ec2__Instance__Info` gained `instance_type : Safe_Str__Text` (read from `sg:instance-type` tag with AWS-side fallback).
- `Ec2__Service` gained `delete_all_instances() -> Schema__Ec2__Delete__Response` to support `sp delete --all`.
- New shared helper `_resolve_typer_target(target)` for the "auto-pick when only one instance" UX.

Step 4 added the `DELETE /ec2/playwright/delete-all` route — calls `service.delete_all_instances()`.

Tests: 24 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py`.

#### `image/Image__Build__Service` (Phase A step 2)

Replaces ~70% of duplicated build logic between `Build__Docker__SGraph_AI__Service__Playwright` and `Docker__SP__CLI`. Both compose a Type_Safe `Schema__Image__Build__Request` and hand it to the shared service.

| File | Role |
|------|------|
| `image/schemas/Schema__Image__Stage__Item.py` | One file or tree to copy (`source_path`, `target_name`, `is_tree`, `extra_ignore_names`) |
| `image/schemas/Schema__Image__Build__Request.py` | `image_folder`, `image_tag`, `stage_items`, `dockerfile_name='dockerfile'`, `requirements_name='requirements.txt'`, `build_context_prefix` |
| `image/schemas/Schema__Image__Build__Result.py` | `image_id`, `image_tags`, `duration_ms` |
| `image/collections/List__Schema__Image__Stage__Item.py` | Ordered list (later overrides earlier) |
| `image/service/Image__Build__Service.py` | Two seams: `stage_build_context()` (pure I/O) and `build()` (Docker SDK direct — bypasses osbot-docker `@catch`) |

Tests: 15 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/image/`.

---

### Phase B sister sections (2026-04-26 → 2026-04-29) — complete

Per-stack-type sister sections, each self-contained (folder per section, never cross-imports). All four were complete at v0.1.31:

| Section | Folder | What it provisions | Tests |
|---------|--------|--------------------|-------|
| `sp os` (long) / `sp opensearch` | `opensearch/` | Single-node OpenSearch 2.x + Dashboards on EC2; nginx-free; Dashboards on `:443` | 131 unit tests |
| `sp prom` / `sp prometheus` | `prometheus/` | Prometheus + cadvisor + node-exporter on EC2; Prom UI on `:9090`; **no Grafana** (P1); ephemeral with 24h retention (P2); baked scrape targets (P3); moving `:latest` image tags (P4) | 170 unit tests |
| `sp vnc` | `vnc/` | Chromium + nginx + mitmproxy stack with KasmVNC viewer on `:443`; mitmproxy auth shared with nginx Basic; interceptor model default-off + baked examples + inline source (N5) | 189 unit tests |
| `sp el` | `elastic/` | Pre-existing Elastic / Kibana stack — the model the other three sections mirror |

Common structure per section:

- `primitives/` — `Safe_Str__{Section}__Stack__Name`, `Safe_Str__{Section}__Password` (where applicable), `Safe_Str__IP__Address` (section-local copy).
- `enums/` — `Enum__{Section}__Stack__State` (parity locked by test across all sections).
- `schemas/` — Create request / response, Info, List, Delete response, Health.
- `collections/` — `List__Schema__{Section}__Stack__Info`.
- `service/` — `{Section}__AWS__Client` (composition shell), `SG__Helper`, `AMI__Helper`, `Instance__Helper`, `Tags__Builder`, `HTTP__Base`, `HTTP__Probe`, `Caller__IP__Detector`, `Random__Stack__Name__Generator`, `Stack__Mapper`, `Compose__Template`, `User_Data__Builder`, `Launch__Helper`, `{Section}__Service`.
- `fast_api/routes/Routes__{Section}__Stack.py` — 5 endpoints under `/{section}/`.
- `cli/Renderers.py` — Rich renderers (pure functions, no service/AWS/HTTP calls).
- `scripts/{section}.py` — Typer entry point mounted on the main `sp` app via `add_typer`.

Every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no mocks).

---

### `vnc/` — N5 interceptor selector

`Enum__Vnc__Interceptor__Kind` — `NONE` (default), `NAME` (baked example), `INLINE` (operator-supplied source). `Vnc__Interceptor__Resolver` ships three baked examples (`header_logger`, `header_injector`, `flow_recorder`). The interceptor tag on EC2 carries `'none'` / `'name:{ex}'` / `'inline'`; the source itself never goes in a tag.

`Schema__Vnc__Interceptor__Choice` carries `kind + name + inline_source`. `scripts/vnc.py` accepts `--interceptor <name>` (baked) or `--interceptor-script <path>` (local file → INLINE); raises `BadParameter` if both.

---

### Phase C — Strip the Playwright EC2 (2026-04-29)

The Playwright EC2 now hosts only 2 containers: `playwright` + `agent-mitmproxy`. The prior 9-container compose (browser + browser-proxy + cadvisor + node-exporter + prometheus + fluent-bit + dockge + the 2 retained) was split out — each moved container lives in its own sister section, Dockge was deleted entirely.

| Surface | Before | After |
|---------|--------|-------|
| Containers on Playwright EC2 | 9 | **2** |
| `scripts/provision_ec2.py` LoC | ~2,950 | ~2,690 |
| `Ec2__AWS__Client.SG_INGRESS_PORTS` | `(8000, 8001, 3000)` | `(8000, 8001)` |
| Named volumes | `prometheus_data` | none |
| `render_compose_yaml(...)` signature | 11 params | 9 params |
| `render_user_data(...)` signature | 9 params | 6 params |

Constants kept-for-now (deleted in Phase D when their last consumer goes): `EC2__BROWSER_INTERNAL_PORT`, `EC2__BROWSER_IMAGE`, `EC2__DOCKGE_PORT`, `EC2__DOCKGE_IMAGE`, `EC2__PROMETHEUS_PORT`.

Tests updated: `test_render_compose_yaml` assertions tightened (restart-count `== 2`; new defensive `test__no_browser_or_observability_services`); entire `test_render_observability_configs` class (8 tests) removed.

---

### Phase D — Command cleanup (2026-04-29)

Per plan doc 7 (C1 hard cut, no transition window). Four sub-slices:

**D.1 — Drop `forward-*` typer commands:**
- `sp forward-prometheus` → `sp prom forward <name>` (when that lands)
- `sp forward-browser` → `sp vnc connect <name>`
- `sp forward-dockge` → deleted entirely (Dockge dropped)

**D.2 — Move `sp metrics` → `sp prom metrics <url>`** — URL-based fetch of any `/metrics` endpoint.

**D.3 — Regroup `sp vault-*` under `sp vault` subgroup:**
- `sp vault-{clone,list,run,commit,push,pull,status}` → `sp vault {clone,list,run,commit,push,pull,status}`
- `sp v` short alias (hidden)

**D.4 — Regroup `sp *-ami` under `sp ami` subgroup**:
- `sp bake-ami` → `sp ami create`
- `sp wait-ami` → `sp ami wait`
- `sp tag-ami` → `sp ami tag`
- `sp list-amis` → `sp ami list`
- `sp create-from-ami` stays top-level (different action)

Orphaned constants removed: `EC2__BROWSER_INTERNAL_PORT` (in `Ec2__AWS__Client`); `EC2__PROMETHEUS_PORT` / `EC2__BROWSER_IMAGE` / `EC2__DOCKGE_PORT` / `EC2__DOCKGE_IMAGE` (in `provision_ec2.py`). `sp open` URL hints, `sp diagnose` port grep, and `provision()` return dict's `browser_url` all dropped.

---

### v0.1.96 — playwright stack-split — done

| Phase | Status | Output |
|-------|--------|--------|
| **A** — shared foundations | done | `Stack__Naming`, `Image__Build__Service`, `Ec2__AWS__Client` |
| **B5** — `sp os` | done | OpenSearch + Dashboards |
| **B6** — `sp prom` | done | Prometheus + cAdvisor + node-exporter |
| **B7** — `sp vnc` | done | chromium + nginx + mitmproxy |
| **C** — strip Playwright EC2 | done | 9 containers → 2 |
| **D** — command cleanup | done | flat `vault-*` / `*-ami` regrouped; `forward-*` + `metrics` dropped/moved |

---

## See also

- Parent: [`index.md`](index.md)
- Source: [`_archive/v0.1.31/06__sp-cli-duality-refactor.md`](../_archive/v0.1.31/06__sp-cli-duality-refactor.md)
