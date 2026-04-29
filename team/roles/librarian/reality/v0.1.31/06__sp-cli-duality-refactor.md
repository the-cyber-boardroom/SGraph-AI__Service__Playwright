# Reality — SP CLI / FastAPI Duality Refactor

**Status:** partial — read-only surface + delete mutation implemented.
Other mutation ops (create/backup/restore/dashboard-import/data-export/data-import) and CLI wrappers still PROPOSED.

This file tracks what exists today for the refactor proposed in
[`team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md`](../../../../comms/briefs/v0.1.72__sp-cli-fastapi-duality.md).
Everything in the brief that is NOT listed below is still PROPOSED.

---

## New top-level package — `sgraph_ai_service_playwright__cli/`

Sibling of `sgraph_ai_service_playwright/` and `agent_mitmproxy/`. Houses the
Type_Safe refactor of the `sp` / `ob` CLI. Nothing under
`sgraph_ai_service_playwright/` was modified. Package version: `v0.0.1`.

### `aws/` — shared AWS infrastructure helpers (Phase A step 1, 2026-04-26)

Single source of truth for naming conventions every sister section needs.

| File | Role |
|------|------|
| `aws/Stack__Naming.py` | Type_Safe class binding a `section_prefix` (e.g. `elastic`, `opensearch`, `prometheus`, `vnc`) once and exposing `aws_name_for_stack()` (Name tag with section prefix; never doubled) + `sg_name_for_stack()` (SG GroupName with `-sg` suffix; never starts with reserved `sg-`). |

The previously-elastic-only module-level functions in `elastic/service/Elastic__AWS__Client.py` (`aws_name_for_stack`, `sg_name_for_stack`) were removed. `Elastic__AWS__Client.py` now declares `ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')` at module level; the 5 prior call sites (2 in `Elastic__AWS__Client`, 2 in `Elastic__Service`, 1 in the in-memory test client) use this shared instance. Future `sp os`, `sp prom`, `sp vnc` sections each get their own `*_NAMING` constant pointing at the same `Stack__Naming` class.

Tests: 9 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py` cover prefix-when-missing / no-double-prefix / partial-match-non-counting / per-section-isolation / sg-suffix universality. Plan reference: `team/comms/plans/v0.1.96__playwright-stack-split__02__api-consolidation.md`.

### `ec2/service/Ec2__AWS__Client.py` — central EC2 AWS boundary (Phase A steps 3a–3d, 3f, 2026-04-26)

In step 3f, three typer commands (`cmd_list`, `cmd_info`, `cmd_delete`) reduced to thin wrappers over `Ec2__Service`:

- `Schema__Ec2__Instance__Info` gained `instance_type : Safe_Str__Text` (read from the `sg:instance-type` tag with fallback to the AWS-side `instance_type` field).
- `Ec2__Service` gained `delete_all_instances() -> Schema__Ec2__Delete__Response` to support `sp delete --all` without the typer command iterating directly.
- `cmd_info` is now ~40 lines (was ~60+); body = call service, render with new `_render_info()` Tier-2A helper.
- `cmd_delete` is now a thin wrapper that calls either `delete_instance(target)` or `delete_all_instances()`.
- `cmd_list` keeps its inline AMI-source map + launch-time fetch (still needs raw boto3 due to osbot's `LauchTime` typo) but reads instance basics from `Ec2__Service().list_instances()`.
- New shared helper `_resolve_typer_target(target)` handles the "auto-pick when only one instance" UX. The older `_resolve_target` stays in place for the 12 typer commands that still need raw `details`; those reduce in a future slice.

In step 4, the previously CLI-only `sp delete --all` op gets an HTTP route:

- `DELETE /ec2/playwright/delete-all` — calls `service.delete_all_instances()`. Returns `Schema__Ec2__Delete__Response` with empty `target` / `deploy_name` and a populated `terminated_instance_ids`. Route registered in `Routes__Ec2__Playwright.setup_routes()` alongside the other lifecycle routes.
- `Ec2__Service__In_Memory` (the test fixture) gained a matching `delete_all_instances()` override.

Other typer commands (`connect`, `shell`, `exec`, `forward`, `wait`, `screenshot`, `smoke`, `bake-ami`, `wait-ami`, `tag-ami`, etc.) are interactive (SSM session, port-forwarding, screenshots) — they do not naturally fit a stateless HTTP request/response and were not added as routes.

Mirrors the `Elastic__AWS__Client` pattern. Hosts the previously-private helpers that lived in `scripts/provision_ec2.py`:

| Surface | Symbol | Form |
|---------|--------|------|
| Module-level pure helpers | `random_deploy_name`, `get_creator`, `uptime_str`, `instance_tag`, `instance_deploy_name` | Functions; no AWS calls. Naming pools `_ADJECTIVES` / `_SCIENTISTS` live alongside. |
| Module-level constants | `TAG__SERVICE_KEY`, `TAG__SERVICE_VALUE`, `TAG__DEPLOY_NAME_KEY`, `INSTANCE_STATES_LIVE` | Tag/state values used by find / resolve / terminate. |
| Type_Safe class | `Ec2__AWS__Client` | Methods: `ec2()` (single seam, tests override); `find_instances()`; `find_instance_ids()`; `resolve_instance_id(target)`; `terminate_instances(nickname)`. Each EC2 call goes through `self.ec2()` so an in-memory test double can replace the boto3 boundary. |
| AWS context accessors (3b) | `aws_account_id`, `aws_region`, `ecr_registry_host`, `default_playwright_image_uri`, `default_sidecar_image_uri` | Module-level functions over `osbot_aws.AWS_Config`. `PLAYWRIGHT_IMAGE_NAME` + `SIDECAR_IMAGE_NAME` re-exported from the docker base modules. |
| IAM constants + helpers (3c) | `IAM__ROLE_NAME`, `IAM__ECR_READONLY_POLICY_ARN`, `IAM__SSM_CORE_POLICY_ARN`, `IAM__POLICY_ARNS`, `IAM__PROMETHEUS_RW_POLICY_ARN`, `IAM__OBSERVABILITY_POLICY_ARNS`, `IAM__ASSUME_ROLE_SERVICE`, `IAM__PASSROLE_POLICY_NAME`; functions `decode_aws_auth_error(exc)`, `ensure_caller_passrole(account)`, `ensure_instance_profile()` | Module-level. The Console-formatted `_print_auth_error` stays in `provision_ec2.py` (Tier 2A — CLI rendering); `ensure_caller_passrole` no longer prints on auth failure (just raises) — the typer command is now responsible for auth-error formatting. |
| SG + AMI constants (3d) | `SG__NAME`, `SG__DESCRIPTION`, `EC2__AMI_OWNER_AMAZON`, `EC2__AMI_NAME_AL2023`, `EC2__PLAYWRIGHT_PORT`, `EC2__SIDECAR_ADMIN_PORT`, `EC2__BROWSER_INTERNAL_PORT`, `SG_INGRESS_PORTS`, `TAG__AMI_STATUS_KEY` | Module-level. **Bug fix:** `SG__DESCRIPTION` lost its em-dash (AWS rejects non-ASCII `GroupDescription` — see Elastic precedent). Phase C will drop `EC2__BROWSER_INTERNAL_PORT` from `SG_INGRESS_PORTS`. |
| SG + AMI methods (3d) | `Ec2__AWS__Client.ensure_security_group()`, `latest_al2023_ami_id()`, `create_ami(instance_id, name)`, `wait_ami_available(ami_id, timeout=900)`, `tag_ami(ami_id, status)`, `latest_healthy_ami()` | All AWS-touching; go through `self.ec2()` so an in-memory `_Fake_EC2` (with a `_Fake_Boto3_Client`) covers the AMI lifecycle paths. The wrappers in `provision_ec2.py` keep the old `(ec2: EC2)` signatures for callsite stability. |

`scripts/provision_ec2.py` keeps wrapper functions matching the old signatures (`find_instances(ec2: EC2 = None)`, `terminate_instances(ec2: EC2 = None, nickname='')`, etc.) that delegate to a module-level `Ec2__AWS__Client()` instance. The `ec2` parameter is now optional and ignored — callers in `provision_ec2.py` keep working unchanged. These wrappers go away in Phase A step 3f when typer commands become thin wrappers over `Ec2__Service`.

`Ec2__Service` no longer imports lookup helpers from `scripts.provision_ec2` (only the EC2 port constants + tag-name constants remain as imports). Its `list_instances`, `get_instance_info`, `delete_instance`, and `resolve_target` methods now use a `Ec2__AWS__Client` instance via the `aws_client()` seam.

Tests: 24 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/ec2/service/test_Ec2__AWS__Client.py` cover every helper + every class method. AWS calls go through an in-memory `_Fake_EC2` (real subclass, no mocks).

### `image/` — shared Docker image build pipeline (Phase A step 2, 2026-04-26)

Replaces ~70% of duplicated build logic between `Build__Docker__SGraph_AI__Service__Playwright` (Playwright EC2 image) and `Docker__SP__CLI` (SP CLI Lambda image). Both now compose a Type_Safe `Schema__Image__Build__Request` and hand it to the shared service.

| File | Role |
|------|------|
| `image/schemas/Schema__Image__Stage__Item.py` | One file or directory tree to copy into the build context (`source_path`, `target_name`, `is_tree`, `extra_ignore_names`). |
| `image/collections/List__Schema__Image__Stage__Item.py` | Ordered list of stage items (later overrides earlier). |
| `image/collections/List__Str.py` | Typed list of strings (used for `image_tags` + `extra_ignore_names`). |
| `image/schemas/Schema__Image__Build__Request.py` | Inputs: `image_folder` (dockerfile + requirements live here), `image_tag`, `stage_items`, `dockerfile_name='dockerfile'`, `requirements_name='requirements.txt'`, `build_context_prefix`. |
| `image/schemas/Schema__Image__Build__Result.py` | Outputs: `image_id`, `image_tags`, `duration_ms`. |
| `image/service/Image__Build__Service.py` | Orchestrator. Two seams: `stage_build_context()` (pure I/O — exhaustively unit-testable) and `build()` (invokes the docker SDK directly to bypass osbot-docker's @catch wrapper). Default ignore set (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `*.pyc`) is augmented per-item via `extra_ignore_names`. |

Both consumers reduce to thin composers:
- `Build__Docker__SGraph_AI__Service__Playwright.build_docker_image()` returns `Schema__Image__Build__Result`. Composes 3 stage items: `lambda_entry.py` (file), `image_version` (file), `sgraph_ai_service_playwright` (tree).
- `Docker__SP__CLI.build_and_push()` returns the existing dict shape (kept for now: the deploy callers consume `image_uri`/`image_id`/`push` keys). Composes 4 stage items: `sgraph_ai_service_playwright__cli` (tree, `extra_ignore_names=['images']`), `sgraph_ai_service_playwright`, `agent_mitmproxy`, `scripts` (all trees).

Tests: 15 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/image/` cover schema round-trip, default values, stage-context happy path (file + tree + custom-name + extra-ignores), `build()` happy path with an in-memory fake docker client (no daemon required), tempdir-cleanup-on-failure, and ignore-callable composition. Existing consumer tests rewired: `tests/unit/sgraph_ai_service_playwright__cli/deploy/test_Docker__SP__CLI.py` lost its now-redundant `ignore_build_noise` tests (the behaviour moved to `Image__Build__Service`) and gained `test_build_request__has_all_four_source_trees_with_correct_target_names`. The deploy-via-pytest integration test `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py` updated to assert on `Schema__Image__Build__Result` fields instead of dict keys.

### `opensearch/` — `sp os` sister section (Phase B steps 5a–5f.4, 2026-04-26)

First two slices of the new OpenSearch sister section. Folder name is `opensearch/` (not `os/`) — `os` shadows the Python stdlib `os` module and breaks `import os` inside the package. The typer command alias stays `sp os` / `sp opensearch`.

| File | Role |
|------|------|
| `opensearch/primitives/Safe_Str__OS__Stack__Name.py` | Logical name for an ephemeral OS+Dashboards stack. Same regex as `Safe_Str__Elastic__Stack__Name`. |
| `opensearch/primitives/Safe_Str__OS__Password.py` | Admin password (URL-safe base64, 16-64 chars). Mirrors `Safe_Str__Elastic__Password`. |
| `opensearch/primitives/Safe_Str__IP__Address.py` | Local copy of the IP-address primitive (sister sections stay self-contained; promotion to a shared location is a future cleanup). |
| `opensearch/enums/Enum__OS__Stack__State.py` | Lifecycle state vocabulary (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN). Mirrors `Enum__Elastic__State`. |
| `opensearch/schemas/Schema__OS__Stack__Create__Request.py` | Create inputs — all fields optional, mirrors elastic create request. |
| `opensearch/schemas/Schema__OS__Stack__Create__Response.py` | Returned once on create; carries the generated `admin_password`, the `dashboards_url`, and the `os_endpoint`. |
| `opensearch/schemas/Schema__OS__Stack__Info.py` | Public view of one stack — never includes `admin_password`. |
| `opensearch/schemas/Schema__OS__Stack__List.py` | Response wrapper for `list_stacks()`. |
| `opensearch/schemas/Schema__OS__Stack__Delete__Response.py` | Empty fields ⇒ route returns 404. |
| `opensearch/schemas/Schema__OS__Health.py` | Cluster + Dashboards health snapshot; `-1` sentinels mark unreachable probes. |
| `opensearch/collections/List__Schema__OS__Stack__Info.py` | Type_Safe__List for the listing response. |
| `opensearch/service/OpenSearch__AWS__Client.py` | Composition shell — declares tag constants + `OS_NAMING`, exposes `sg` / `ami` / `instance` / `tags` slots wired by `setup()`. **Per-concern helpers below live in their own files** (one class per file per CLAUDE.md rule #21) so each can be reviewed and edited in isolation. |
| `opensearch/service/OpenSearch__SG__Helper.py` | `ensure_security_group(region, stack_name, caller_ip)` — idempotent SG create + ingress on Dashboards port 443; `delete_security_group(region, sg_id)`. ASCII-only Description (AWS rejects multi-byte). |
| `opensearch/service/OpenSearch__AMI__Helper.py` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=opensearch` + `sg:ami-status=healthy` (returns empty string if none). |
| `opensearch/service/OpenSearch__Instance__Helper.py` | `list_stacks(region)` returns `{instance_id: details}` filtered by `sg:purpose=opensearch` + live states; `find_by_stack_name(region, stack_name)`; `terminate_instance(region, instance_id)`. |
| `opensearch/service/OpenSearch__Tags__Builder.py` | Pure mapper — builds the canonical 6-tag list (Name, sg:purpose, sg:section, sg:stack-name, sg:allowed-ip, sg:creator). Creator falls back to 'unknown' when empty. |
| `opensearch/service/OpenSearch__HTTP__Base.py` | Request seam wrapping `requests` with `verify=False` (self-signed cert at boot), Basic auth, scoped urllib3 InsecureRequestWarning suppression. Tests substitute `requests.request` via a recorder. |
| `opensearch/service/OpenSearch__HTTP__Probe.py` | Read-only probes — `cluster_health(base_url, ...)` (returns `{}` on unreachable / non-200 / non-JSON; caller maps to `-1` sentinels in `Schema__OS__Health`); `dashboards_ready(base_url, ...)` (True on 2xx). Composes `OpenSearch__HTTP__Base`. |
| `opensearch/service/Caller__IP__Detector.py` | Fetches caller's public IPv4 from `https://checkip.amazonaws.com`; tests subclass and override `fetch()`. Section-local copy. |
| `opensearch/service/Random__Stack__Name__Generator.py` | `'<adjective>-<scientist>'` generator; pools match the elastic vocabulary by design. |
| `opensearch/service/OpenSearch__Stack__Mapper.py` | Pure mapper: raw boto3 `describe_instances` detail dict → `Schema__OS__Stack__Info`. State enum mapping locked by tests. |
| `opensearch/service/OpenSearch__Compose__Template.py` | Renders docker-compose.yml for single-node OpenSearch + Dashboards (memlock + ulimits + sg-net network + named volume). Tests can pin image tags (production uses `:latest` per OS1). |
| `opensearch/service/OpenSearch__User_Data__Builder.py` | Renders the EC2 UserData bash. Installs Docker via `dnf`, installs the docker compose plugin, writes the rendered compose YAML to `/opt/sg-opensearch/docker-compose.yml`, bumps `vm.max_map_count` (required for OS 2.x), runs `docker compose up -d`. `admin_password` lives only inside compose_yaml — secrets in one place. |
| `opensearch/service/OpenSearch__Launch__Helper.py` | Single-purpose `run_instance(region, ami_id, sg_id, user_data, tags, instance_type, instance_profile_name?)`. Base64-encodes UserData; pins `MinCount=MaxCount=1` (single-node stack). Composed in `OpenSearch__AWS__Client.launch`. |
| `opensearch/service/OpenSearch__Service.py` | Tier-1 orchestrator. Exposes `create_stack(request, creator)`, `list_stacks(region)`, `get_stack_info(region, stack_name)`, `delete_stack(region, stack_name)`, `health(region, stack_name, username, password)`. `create_stack` resolves all defaults (random `os-{adj}-{sci}` name, caller IP via detector, `secrets.token_urlsafe(24)` admin password, latest AL2023 AMI, region default), then composes SG + tags + compose + user-data + launch. Tests cover empty-request-resolves-defaults / request-overrides-take-priority / secret-only-flows-via-compose / sg-uses-resolved-ip / launch-call-shape. |

131 unit tests across primitives / enums / schemas / collections / AWS helpers / HTTP base + probe / compose template / user-data builder / launch helper / mapper / service (read paths + create_stack) / composition. Every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no mocks); each helper has its own focused test file kept under ~150 lines.

### `prometheus/` — `sp prom` sister section (Phase B steps 6a–6h, 2026-04-26 → 2026-04-28) — **complete**

**`sp prom` is functionally complete end-to-end.** Tier-1 `Prometheus__Service` + Tier-2A `scripts/prometheus.py` typer + Tier-2B FastAPI routes are all in place. Folder `prometheus/`; typer aliases `sp prom` (short, hidden) + `sp prometheus` (long), mounted on the main `sp` app via `add_typer`. Per plan doc 5: no Grafana (P1 — runs from cloud/hosted); ephemeral with no EBS and 24 h retention (P2); one-shot baked scrape targets (P3); moving `latest` image tags (P4).

| File | Role |
|------|------|
| `prometheus/primitives/Safe_Str__Prom__Stack__Name.py` | Stack name; same regex as elastic + opensearch (parity locked by test). |
| `prometheus/primitives/Safe_Str__IP__Address.py` | Local IPv4 primitive. Sister sections stay self-contained. |
| `prometheus/enums/Enum__Prom__Stack__State.py` | Lifecycle vocabulary (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN); shape parity with elastic + opensearch locked by test. |
| `prometheus/service/Prometheus__AWS__Client.py` | Composition shell — declares `PROM_NAMING = Stack__Naming(section_prefix='prometheus')` + 6 tag constants (`sg:purpose=prometheus`, `sg:section=prom`). `setup()` wires `sg`/`ami`/`instance`/`tags` slots; Launch helper joins in step 6f.4a. |
| `prometheus/service/Prometheus__SG__Helper.py` | `ensure_security_group(region, stack_name, caller_ip)` — idempotent SG create + ingress on **port 9090** (Prometheus' own UI; no nginx because P1 says no UI in this stack); ASCII-only Description; duplicate-ingress swallowed. `delete_security_group(region, sg_id) -> bool`. |
| `prometheus/service/Prometheus__AMI__Helper.py` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=prometheus` + `sg:ami-status=healthy` (returns empty string if none). |
| `prometheus/service/Prometheus__Instance__Helper.py` | `list_stacks(region)` returns `{instance_id: details}` filtered by `sg:purpose=prometheus` + live states; `find_by_stack_name(region, stack_name)`; `terminate_instance(region, instance_id) -> bool`. |
| `prometheus/service/Prometheus__Tags__Builder.py` | Pure mapper — builds the canonical 6-tag list (Name, sg:purpose, sg:section, sg:stack-name, sg:allowed-ip, sg:creator). Name uses `PROM_NAMING.aws_name_for_stack` (prefix never doubles). Empty creator → `'unknown'`. |
| `prometheus/service/Prometheus__HTTP__Base.py` | Request seam wrapping `requests` with `verify=False` default + scoped urllib3 InsecureRequestWarning suppression + Basic auth seam. Adds a `params` kwarg (used by `/api/v1/query`). |
| `prometheus/service/Prometheus__HTTP__Probe.py` | Three read-only probes: `prometheus_ready` (True on 2xx of `/-/healthy`); `targets_status` (parsed `/api/v1/targets`; `{}` on failure — caller derives `targets_total` / `targets_up` from `data.activeTargets`); `query` (forwards PromQL via `/api/v1/query?query=…` for the future `sp prom query` command). Composes `Prometheus__HTTP__Base`. |
| `prometheus/service/Caller__IP__Detector.py` | Fetches caller's public IPv4 from `https://checkip.amazonaws.com`; tests subclass and override `fetch()`. Section-local copy. |
| `prometheus/service/Random__Stack__Name__Generator.py` | `'<adjective>-<scientist>'` generator; pools match the elastic + opensearch vocabulary by design (parity test). |
| `prometheus/service/Prometheus__Stack__Mapper.py` | Pure mapper — raw boto3 `describe_instances` detail dict → `Schema__Prom__Stack__Info`. Builds `prometheus_url = http://<ip>:9090/` (plain HTTP per P1; empty when AWS hasn't assigned the IP yet). State enum mapping locked by test. |
| `prometheus/service/Prometheus__Compose__Template.py` | Renders docker-compose.yml — 3 services (`prometheus` + `cadvisor` + `node-exporter`) on `sg-net` bridge. Bind-mounts `/opt/sg-prometheus/prometheus.yml` into the prometheus container. `--storage.tsdb.retention.time=24h` per P2. Images use moving `:latest` per P4; tests pin known versions. Container names `sg-prometheus` / `sg-cadvisor` / `sg-node-exporter`. **No Grafana / Dashboards** per P1 (locked by test). |
| `prometheus/service/Prometheus__Config__Generator.py` | Renders `prometheus.yml`. Always emits a baseline scrape config (cadvisor + node-exporter) + appends one job per caller-supplied `Schema__Prom__Scrape__Target` (P3 — baked at create time; the dynamic `sp prom add-target` flow is deferred). |
| `prometheus/service/Prometheus__User_Data__Builder.py` | Renders the EC2 UserData bash. Installs Docker via `dnf`, installs the docker compose plugin, writes both `prometheus.yml` and the rendered compose YAML to `/opt/sg-prometheus/`, runs `docker compose up -d`. **No `vm.max_map_count` bump** (Prom doesn't need it — that's an OS 2.x requirement). |
| `prometheus/service/Prometheus__Launch__Helper.py` | Single-purpose `run_instance(region, ami_id, sg_id, user_data, tags, instance_type, instance_profile_name?)`. Base64-encodes UserData; pins `MinCount=MaxCount=1`. `DEFAULT_INSTANCE_TYPE=t3.medium` (smaller than sp os because Prom + 2 exporters are lightweight). Wired into `Prometheus__AWS__Client.launch`. |
| `prometheus/service/Prometheus__Service.py` | Tier-1 orchestrator. Exposes `create_stack(request, creator='')`, `list_stacks(region)`, `get_stack_info(region, stack_name)`, `delete_stack(region, stack_name)`, `health(region, stack_name)`. `create_stack` resolves all defaults (random `prom-{adj}-{sci}` name, caller IP via detector, latest AL2023 AMI, region default, `t3.medium`), composes SG + tags + compose + prometheus.yml + user-data + launch. `setup()` lazy-wires `aws_client` + `probe` + `mapper` + `ip_detector` + `name_gen` + `compose_template` + `config_generator` + `user_data_builder` (8 helpers). Tests cover empty-request / overrides / scrape-targets-flow / sg-uses-resolved-ip / launch-call-shape / user-data-receives-both-yamls. |
| `prometheus/fast_api/routes/Routes__Prometheus__Stack.py` | 5 FastAPI routes mirroring `Routes__OpenSearch__Stack`. URL prefix `/prometheus`. `POST /prometheus/stack`, `GET /prometheus/stacks`, `GET/DELETE /prometheus/stack/{name}` (404 on miss), `GET /prometheus/stack/{name}/health`. Handlers carry zero logic — `service.method().json()`. The `create` handler takes `body: dict` and round-trips via `Schema__Prom__Stack__Create__Request.from_json(body)` because FastAPI/pydantic can't auto-generate a schema for the nested `List__Schema__Prom__Scrape__Target` Type_Safe collection. |
| `prometheus/cli/Renderers.py` | Tier-2A Rich renderers — `render_list` / `render_info` / `render_create` / `render_health`. Pure functions; no service / AWS / HTTP calls. State→colour mapping mirrors the OS Renderers. **No password rendered anywhere** (P1 — locked by test). |
| `scripts/prometheus.py` | Typer entry point — `sp prometheus` long form, `sp prom` short alias. 5 commands (`create` / `list` / `info` / `delete` / `health`). Each command body is a thin wrapper: build request, call `Prometheus__Service`, render via the Renderers helper. Mounted on the main `sp` app via `add_typer` in `scripts/provision_ec2.py` (alongside `sp el` / `sp os` / `sp linux` / `sp docker`). |
| `prometheus/schemas/Schema__Prom__Scrape__Target.py` | One scrape job baked into prometheus.yml at create time (P3). `job_name : Safe_Str__Id` + `targets : List__Str` (host:port) + `scheme : Safe_Str__Id = 'http'` + `metrics_path : Safe_Str__Url__Path = '/metrics'`. Slash-preserving primitive chosen after `Safe_Str__Text` test caught the strip. |
| `prometheus/schemas/Schema__Prom__Stack__Create__Request.py` | Inputs for `sp prom create [NAME]`. All fields optional. Includes `scrape_targets : List__Schema__Prom__Scrape__Target` for the baked target list. **No** `admin_password` field (P1: no built-in auth). |
| `prometheus/schemas/Schema__Prom__Stack__Create__Response.py` | Returned once on create. **No** `admin_password` / `admin_username` / `dashboards_url` (P1). Carries `prometheus_url` (http://&lt;ip&gt;:9090/) + `targets_count` + `state`. |
| `prometheus/schemas/Schema__Prom__Stack__Info.py` | Public view of one stack — defensive test asserts no `password` field anywhere. |
| `prometheus/schemas/Schema__Prom__Stack__List.py` | Response wrapper for `list_stacks` — `region` + `stacks`. |
| `prometheus/schemas/Schema__Prom__Stack__Delete__Response.py` | Empty fields ⇒ caller maps to HTTP 404. Reuses `List__Instance__Id` from `cli/ec2/`. |
| `prometheus/schemas/Schema__Prom__Health.py` | Health snapshot — `prometheus_ok` (200 on `/-/healthy`), `targets_total` / `targets_up` (-1 sentinels = unreachable; 0 is a valid 'no targets configured'). |
| `prometheus/collections/List__Schema__Prom__Stack__Info.py` | Type_Safe__List for the listing response. |
| `prometheus/collections/List__Schema__Prom__Scrape__Target.py` | Type_Safe__List for the scrape-job list. |
| `prometheus/collections/List__Str.py` | Local typed list of plain strings (host:port targets). Section-local copy — sister sections stay self-contained. |

170 unit tests across primitives + enums + schemas + collections + AWS helpers + HTTP base + probe + Caller__IP__Detector + Random__Stack__Name__Generator + Stack__Mapper + Compose template + Config generator + User_Data builder + Launch helper + Service (read paths + create_stack + setup() chain) + FastAPI routes (5 endpoints via TestClient) + Renderers (Rich Console-capture) + typer-app smoke (CliRunner). Every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no mocks); each helper has its own focused test file kept under ~150 lines.

### `vnc/` — `sp vnc` sister section (Phase B steps 7a–7g, 2026-04-29)

`sp vnc` Tier-2B HTTP surface is in place; `create_stack` end-to-end works through the in-memory composition fakes. Typer commands (Tier-2A) land in 7h. Folder `vnc/`; typer alias `sp vnc` (single name only — N1: renamed from working title `sp nvm`). Per plan doc 6: chromium-only at runtime today (N2); profile + state wiped at termination (N3); no automatic flow export (N4); interceptor model is **default-off + ship examples + provision-time choice via env vars** (N5).

| File | Role |
|------|------|
| `vnc/primitives/Safe_Str__Vnc__Stack__Name.py` | Stack name; same regex as elastic + opensearch + prometheus (parity locked by test). |
| `vnc/primitives/Safe_Str__IP__Address.py` | Local IPv4 primitive. Sister sections stay self-contained. |
| `vnc/primitives/Safe_Str__Vnc__Password.py` | Operator password (URL-safe base64, 16-64 chars). Used both for nginx Basic auth (operator-facing UI) and `MITM_PROXYAUTH` on the mitmproxy container — service generates one and uses it twice. |
| `vnc/primitives/Safe_Str__Vnc__Interceptor__Source.py` | Raw Python source for an inline interceptor (per N5). Permissive regex (tabs + newlines + printable ASCII); `max_length=32 KB`; `trim_whitespace=False` so indentation survives. |
| `vnc/enums/Enum__Vnc__Stack__State.py` | Lifecycle vocabulary (PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN); shape parity with elastic + os + prom locked by test. |
| `vnc/enums/Enum__Vnc__Interceptor__Kind.py` | N5 interceptor selector — `NONE` (default), `NAME`, `INLINE`. |
| `vnc/service/Vnc__AWS__Client.py` | Composition shell — declares `VNC_NAMING = Stack__Naming(section_prefix='vnc')` + 7 tag constants (`sg:purpose=vnc`, `sg:section=vnc`, plus `sg:interceptor` per N5). `setup()` wires `sg`/`ami`/`instance`/`tags` slots. Launch helper joins in step 7f. |
| `vnc/service/Vnc__SG__Helper.py` | `ensure_security_group(region, stack_name, caller_ip)` — idempotent SG create + ingress on **port 443** (nginx TLS — chromium-VNC + proxied mitmweb); ASCII-only Description; duplicate-ingress swallowed. KasmVNC port 3000 stays SSM-only (not in SG); mitmproxy 8080 is loopback-only on the docker network. `delete_security_group(region, sg_id) -> bool`. |
| `vnc/service/Vnc__AMI__Helper.py` | `latest_al2023_ami_id(region)` (raises if none); `latest_healthy_ami_id(region)` filtered by `sg:purpose=vnc` + `sg:ami-status=healthy` (returns empty string if none). |
| `vnc/service/Vnc__Instance__Helper.py` | `list_stacks(region)` filtered by `sg:purpose=vnc` + live states; `find_by_stack_name(region, stack_name)`; `terminate_instance(region, instance_id) -> bool`. |
| `vnc/service/Vnc__Tags__Builder.py` | Pure mapper — builds the canonical 7-tag list (Name, sg:purpose, sg:section, sg:stack-name, sg:allowed-ip, sg:creator, **sg:interceptor**). Name uses `VNC_NAMING.aws_name_for_stack` (prefix never doubles). The interceptor-tag value follows N5: `'none'` (default-off), `'name:{example}'` (baked example), `'inline'` (operator-supplied source — the source itself never goes in a tag). |
| `vnc/service/Vnc__HTTP__Base.py` | Request seam wrapping `requests` with `verify=False` default + scoped urllib3 InsecureRequestWarning suppression + Basic auth seam (operator credentials front both nginx UI and mitmweb). |
| `vnc/service/Vnc__HTTP__Probe.py` | Three read-only probes: `nginx_ready` (True on 2xx of `/`), `mitmweb_ready` (True on 200 of `/api/flows`), `flows_listing` (parsed JSON list from `/api/flows`; `[]` on any failure). Composes `Vnc__HTTP__Base`. |
| `vnc/service/Caller__IP__Detector.py` | Section-local. Fetches `https://checkip.amazonaws.com`; tests subclass and override `fetch()`. |
| `vnc/service/Random__Stack__Name__Generator.py` | `'<adjective>-<scientist>'` generator; pools match elastic + os + prom (parity test). |
| `vnc/service/Vnc__Stack__Mapper.py` | Pure mapper — raw boto3 `describe_instances` detail dict → `Schema__Vnc__Stack__Info`. Builds `viewer_url = https://<ip>/` and `mitmweb_url = https://<ip>/mitmweb/` (empty when no IP). **Decodes the `sg:interceptor` tag** back into `(kind, name)`: `'none'` → NONE, `'name:{ex}'` → NAME + ex, `'inline'` → INLINE + 'inline'. State enum mapping locked by test. |
| `vnc/service/Vnc__Compose__Template.py` | Renders docker-compose.yml — 3 services (`chromium` + `nginx` + `mitmproxy`) on `sg-net` bridge. Chromium (linuxserver/chromium image at runtime, per N2) runs with `HTTPS_PROXY=http://mitmproxy:8080` and `CHROME_CLI=--browser=chromium`. Nginx exposes only port **443** (TLS terminator + Basic auth + reverse-proxy `/` → chromium and `/mitmweb/` → mitmweb). Mitmproxy runs `mitmweb` with `--set=proxyauth=@/opt/sg-vnc/mitm/proxyauth` and `--scripts=/opt/sg-vnc/interceptors/runtime/active.py` (paths populated by user-data; **no secrets in the YAML** — locked by test). |
| `vnc/service/Vnc__Interceptor__Resolver.py` | N5 selector. Three baked example sources inline (`header_logger` / `header_injector` / `flow_recorder`). `resolve(choice)` returns `(source, label)` — for NONE: `('# sg-vnc: no interceptor active\n', '')`; for NAME: example source + name; for INLINE: operator source verbatim + `'inline'`. `list_examples()` exposes the baked names for `sp vnc interceptors`. |
| `vnc/service/Vnc__User_Data__Builder.py` | EC2 UserData bash. Installs Docker via `dnf` (+ `httpd-tools` for htpasswd, `openssl` for self-signed cert); writes `/opt/sg-vnc/{nginx/conf.d, nginx/htpasswd, nginx/tls/{cert,key}.pem, mitm/proxyauth, interceptors/runtime/active.py, docker-compose.yml}`; runs `docker compose up -d`. `operator_password` is interpolated **once** as a shell variable assignment near the top, then used via `${SG_VNC_OPERATOR_PASSWORD}` for both htpasswd and proxyauth — one secret, two boundaries. |
| `vnc/service/Vnc__Launch__Helper.py` | Single-purpose `run_instance(...)`. Base64-encodes UserData; `MinCount=MaxCount=1`. `DEFAULT_INSTANCE_TYPE=t3.large` (chromium needs RAM headroom for VNC + tabs). Wired into `Vnc__AWS__Client.launch`. |
| `vnc/service/Vnc__Service.py` | Tier-1 orchestrator. Exposes `create_stack(request, creator='')`, `list_stacks(region)`, `get_stack_info(region, stack_name)`, `delete_stack(region, stack_name)`, `health(region, stack_name, ...)`, `flows(region, stack_name, ...)` (per N4 — peek mitmweb flows; no auto-export). `health` flips to READY only when both `nginx_ready` AND `mitmweb_ready` pass. `create_stack` resolves all defaults (random `vnc-{adj}-{sci}` name, caller IP, `secrets.token_urlsafe(24)` operator password, latest AL2023 AMI, `t3.large`), composes interceptor-resolver + SG + tags + compose + user-data + launch. `setup()` lazy-wires 8 helpers (5 read-path + compose + user_data + interceptor_resolver). Includes `_flow_summary_from_mitmweb` pure mapper. |
| `vnc/fast_api/routes/Routes__Vnc__Stack.py` | 5 FastAPI routes mirroring `Routes__Prometheus__Stack`. URL prefix `/vnc`. `POST /vnc/stack`, `GET /vnc/stacks`, `GET/DELETE /vnc/stack/{name}` (404 on miss), `GET /vnc/stack/{name}/health`. The `create` handler takes `body: dict` and round-trips via `Schema__Vnc__Stack__Create__Request.from_json(body)` because the request carries a nested `Schema__Vnc__Interceptor__Choice` (same workaround as `Routes__Prometheus__Stack`). |
| `vnc/fast_api/routes/Routes__Vnc__Flows.py` | One additional route — `GET /vnc/stack/{name}/flows` returns `{"flows": [...summaries]}`. Per N4 there is no auto-export; this is just a peek for human debug. 404 when the stack doesn't exist; otherwise envelope with the (possibly empty) list of `Schema__Vnc__Mitm__Flow__Summary`. |
| `vnc/schemas/Schema__Vnc__Interceptor__Choice.py` | The N5 selector itself — `kind` + `name` (when kind=NAME) + `inline_source` (when kind=INLINE). Defaults to NONE so mitmproxy starts without an interceptor unless explicitly chosen. |
| `vnc/schemas/Schema__Vnc__Stack__Create__Request.py` | Inputs for `sp vnc create [NAME]`. All fields optional; carries `operator_password : Safe_Str__Vnc__Password` (one secret, used twice — nginx + mitm) and `interceptor : Schema__Vnc__Interceptor__Choice`. |
| `vnc/schemas/Schema__Vnc__Stack__Create__Response.py` | Returned once. Carries `viewer_url` (https://&lt;ip&gt;/), `mitmweb_url` (https://&lt;ip&gt;/mitmweb/), `operator_password` (returned once), `interceptor_kind` + `interceptor_name`. |
| `vnc/schemas/Schema__Vnc__Stack__Info.py` | Public view — defensive test asserts no `password` field anywhere. |
| `vnc/schemas/Schema__Vnc__Stack__List.py` | Response wrapper — `region` + `stacks`. |
| `vnc/schemas/Schema__Vnc__Stack__Delete__Response.py` | Empty fields ⇒ caller maps to HTTP 404. |
| `vnc/schemas/Schema__Vnc__Health.py` | Health snapshot — `nginx_ok` (200 on `/`) + `mitmweb_ok` (`/api/flows` reachable) + `flow_count` (`-1` sentinel = unreachable; 0 valid). |
| `vnc/schemas/Schema__Vnc__Mitm__Flow__Summary.py` | One-line summary of a mitmweb flow (per N4 no auto-export — flows die with the EC2; this is just a human-debug peek). |
| `vnc/collections/List__Schema__Vnc__Stack__Info.py` | Type_Safe__List for the listing response. |
| `vnc/collections/List__Schema__Vnc__Mitm__Flow__Summary.py` | Type_Safe__List for the flows endpoint. |

174 unit tests — primitives + enums + schemas + collections + AWS helpers + HTTP base + probe + Caller__IP__Detector + Random__Stack__Name__Generator + Stack__Mapper + Compose template + Interceptor resolver + User_Data builder + Launch helper + Service (read paths + flows + create_stack + setup() chain) + FastAPI Stack routes (5 endpoints) + FastAPI Flows route (1 endpoint). Every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no mocks); each helper has its own focused test file kept under ~150 lines.

### `observability/` — Tier-1 pure-logic service (read-only surface)

| File | Role |
|------|------|
| `primitives/Safe_Str__Stack__Name.py` | AWS OS-domain-name compliant stack identifier (3-28 chars, lowercase, starts with letter). |
| `primitives/Safe_Str__AWS__Region.py` | AWS region code (MATCH regex). Empty allowed = resolve at runtime. |
| `primitives/Safe_Str__AWS__Endpoint.py` | AWS service endpoint hostname (no scheme). |
| `primitives/Safe_Int__Document__Count.py` | OS doc count; `-1` sentinel = not queried. |
| `enums/Enum__Stack__Component__Status.py` | Normalised lifecycle state across AMP/OS/AMG. |
| `enums/Enum__Stack__Component__Kind.py` | Identifies which AWS service a component represents. |
| `enums/Enum__Component__Delete__Outcome.py` | Per-component delete result code — DELETED / NOT_FOUND / FAILED. |
| `schemas/Schema__Stack__Component__AMP.py` | AMP workspace view. |
| `schemas/Schema__Stack__Component__OpenSearch.py` | OpenSearch domain view. |
| `schemas/Schema__Stack__Component__Grafana.py` | AMG workspace view. |
| `schemas/Schema__Stack__Info.py` | Aggregate stack view (AMP + OS + AMG; each nullable). |
| `schemas/Schema__Stack__List.py` | `list_stacks` response envelope (carries region). |
| `schemas/Schema__Stack__Component__Delete__Result.py` | Per-component delete outcome (kind + outcome + resource_id + error_message). |
| `schemas/Schema__Stack__Delete__Response.py` | `delete_stack` response envelope (name, region, results). |
| `collections/List__Stack__Info.py` | `Type_Safe__List` subclass for `Schema__Stack__Info`. |
| `collections/List__Stack__Component__Delete__Result.py` | `Type_Safe__List` subclass for delete results. |
| `service/Observability__AWS__Client.py` | Isolated boto3 + SigV4 boundary. **Only file in this package that imports boto3.** Methods: `amp_workspaces`, `opensearch_domains`, `amg_workspaces`, `opensearch_document_count`, `amp_delete_workspace`, `opensearch_delete_domain`, `amg_delete_workspace`. |
| `service/Observability__Service.py` | Pure logic: `list_stacks`, `get_stack_info`, `delete_stack`, `resolve_region`. |

### Tests (26 passing, 0 skipped)

| File | Coverage |
|------|----------|
| `tests/unit/sgraph_ai_service_playwright__cli/observability/primitives/test_Safe_Str__Stack__Name.py` | 7 cases — valid/invalid names, length boundaries, auto-init empty. |
| `tests/unit/.../primitives/test_Safe_Str__AWS__Region.py` | 3 cases — valid regions, empty allowed, bad shapes rejected. |
| `tests/unit/.../schemas/test_Schema__Stack__Info.py` | 4 cases — init, composition with components, JSON round-trip, `.obj()` coverage. |
| `tests/unit/.../service/Observability__AWS__Client__In_Memory.py` | In-memory test double (real subclass — no mocks). Fixture fields for listings + delete outcomes. |
| `tests/unit/.../service/test_Observability__Service.py` | 7 cases — list (populated + empty), get (populated / missing / endpoint-less), region resolution. |
| `tests/unit/.../service/test_Observability__Service__delete.py` | 5 cases — all deleted, all missing, partial-missing, forced failure, JSON round-trip. |

---

## What does NOT exist yet (still PROPOSED)

- CLI wrappers in the new package — typer `app` still lives in `scripts/observability.py` and `scripts/provision_ec2.py`. The new `delete_stack` service method is not yet wired to `ob delete`.
- Other mutation operations (`create`, `backup`, `restore`, `dashboard-import`, `data-export`, `data-import`).
- EC2 refactor (`Ec2__Service`) — provision_ec2.py at 2847 lines is untouched.
- FastAPI routes (`/v1/observability/*`).
- GH Actions workflows (`obs-morning.yml`, `obs-evening.yml`).

---

## Known tech-debt items

1. **boto3 usage** — `Observability__AWS__Client` imports boto3 directly, in violation of CLAUDE.md rule 8 (osbot-aws only). No osbot-aws wrapper exists for AMP / OpenSearch / Grafana services yet; the boundary is isolated to one file with a header comment flagging the exception. Swap to osbot-aws when wrappers land.
2. **Safe_Str primitive vs plain-dict key hash mismatch** — `Safe_Str__Stack__Name` has its own `__hash__`; lookups against plain-dict keys need a `str()` normalisation (see `Observability__Service.get_stack_info`). Consider replacing internal `Dict[str, …]` with a `Dict__*` collection subclass keyed by the Safe primitive so the cast disappears.
