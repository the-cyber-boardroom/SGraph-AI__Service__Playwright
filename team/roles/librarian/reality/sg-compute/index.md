# Reality — SG/Compute Domain

**Status:** ACTIVE — seeded in phase-1 (B1), foundations added in phase-2 (B2), pod management in BV2.3, CLI builder in v0.2.6, billing CLI in v0.2.22, vault-publish spec in v0.2.23.
**Last updated:** 2026-05-17 | **Phase:** v0.2.23 (vault-publish spec — subdomain routing cold path)

---

## What exists today (as of phase-2 / B2)

### Packages

| Package | Location | Description |
|---------|----------|-------------|
| `sg_compute` | `sg_compute/` | SDK — primitives, enums, core schemas, Platform interface, EC2 platform, Spec__Loader/Resolver/Registry, Node__Manager |
| `sg_compute_specs` | `sg_compute_specs/` | Spec catalogue — pilot specs (ollama, open_design), both with typed `manifest.py` |
| `sg_compute__tests` | `sg_compute__tests/` | Test suite — 152 tests, mirrors `sg_compute/` and `sg_compute_specs/` layout |

---

### sg_compute/primitives/ — EXISTS

| Class | Path |
|-------|------|
| `Safe_Str__Spec__Id` | `primitives/Safe_Str__Spec__Id.py` |
| `Safe_Str__Node__Id` | `primitives/Safe_Str__Node__Id.py` |
| `Safe_Str__Pod__Name` | `primitives/Safe_Str__Pod__Name.py` |
| `Safe_Str__Stack__Id` | `primitives/Safe_Str__Stack__Id.py` |
| `Safe_Str__Stack__Name` | `primitives/Safe_Str__Stack__Name.py` |
| `Safe_Str__Platform__Name` | `primitives/Safe_Str__Platform__Name.py` |
| `Safe_Str__AWS__Region` | `primitives/Safe_Str__AWS__Region.py` | Canonical AWS region — regex `^[a-z]{2}-[a-z]+-\d+$`, allow_empty=True |
| `Safe_Str__SSM__Path` | `primitives/Safe_Str__SSM__Path.py` | SSM parameter path — regex `^[a-zA-Z0-9/_.\-]*$`, allow_empty=True |
| `Safe_Str__Image__Registry` | `primitives/Safe_Str__Image__Registry.py` | Docker/ECR registry hostname — allow_empty=True |
| `Safe_Str__Docker__Image` | `primitives/Safe_Str__Docker__Image.py` | Full image ref (`registry/repo:tag`, `repo@sha256:digest`) — T2.6c |
| `Safe_Str__Log__Content` | `primitives/Safe_Str__Log__Content.py` | Multi-line log text — no regex, 1 MB cap — T2.6c |
| `Safe_Str__Message` | `primitives/Safe_Str__Message.py` | Short human-readable message/error — max 512, no regex |
| `Safe_Int__Hours` | `primitives/Safe_Int__Hours.py` | Node lifetime in hours — min=1, max=168 |
| `Safe_Int__Max__Hours` | `primitives/Safe_Int__Max__Hours.py` | Max node lifetime (0=no auto-terminate) — min=0, max=168 — T2.6c |
| `Safe_Int__Log__Lines` | `primitives/Safe_Int__Log__Lines.py` | Log line count — min=0 — T2.6c |
| `Safe_Int__Pids` | `primitives/Safe_Int__Pids.py` | Container PID count — min=0 — T2.6c |
| `Safe_Int__Exit__Code` | `primitives/Safe_Int__Exit__Code.py` | POSIX exit code — min=-256, max=256 — v0.2.6 |
| `Safe_Str__Ollama__Model` | `primitives/Safe_Str__Ollama__Model.py` | Ollama model ref `^[a-z0-9._\-:]+$`, max=64 — v0.2.7 |

### sgraph_ai_service_playwright__cli/aws/billing/ — EXISTS (v0.2.22)

Six `sg aws billing` commands backed by AWS Cost Explorer.

#### Primitives

| Class | Path | Notes |
|-------|------|-------|
| `Safe_Decimal__Currency__USD` | `billing/primitives/Safe_Decimal__Currency__USD.py` | Decimal-backed USD; `decimal_places=4`; `min_value=None` (credits are legitimately negative); extends `Safe_Float__Money` |
| `Safe_Str__Aws_Service_Code` | `billing/primitives/Safe_Str__Aws_Service_Code.py` | CE service display name; permissive regex `r'[^A-Za-z0-9 \-().,/&_]'`; `allow_empty=True` |
| `Safe_Str__Iso8601_Date` | `billing/primitives/Safe_Str__Iso8601_Date.py` | YYYY-MM-DD date string |
| `Safe_Str__Aws_Usage_Type` | `billing/primitives/Safe_Str__Aws_Usage_Type.py` | CE usage type string |

#### Enums

| Class | Values |
|-------|--------|
| `Enum__Billing__Granularity` | `DAILY / HOURLY / MONTHLY` |
| `Enum__Billing__Metric` | `UNBLENDED_COST / BLENDED_COST / NET_UNBLENDED_COST / AMORTIZED_COST` |
| `Enum__Billing__Group_By` | `SERVICE / USAGE_TYPE / LINKED_ACCOUNT / REGION` |
| `Enum__Billing__Window_Keyword` | `LAST_48H / LAST_7D / MONTH_TO_DATE` |

#### Schemas (pure data, no methods)

| Class | Key fields |
|-------|------------|
| `Schema__Billing__Window` | `start / end (Safe_Str__Iso8601_Date)`, `granularity (Enum)`, `keyword (str)` |
| `Schema__Billing__Line_Item` | `service (Safe_Str__Aws_Service_Code)`, `amount_usd (Safe_Decimal__Currency__USD)`, `metric (Enum)` |
| `Schema__Billing__Daily_Bucket` | `date`, `total_usd`, `line_items (List__Schema__Billing__Line_Item)` |
| `Schema__Billing__Report` | `window`, `metric`, `group_by`, `buckets`, `total_usd`, `account_id`, `currency='USD'`, `generated_at` |

#### Collections

`List__Schema__Billing__Daily_Bucket`, `List__Schema__Billing__Line_Item`, `List__Schema__Billing__Group` (scaffolded, unused in MVP).

#### Service layer

| Class | Path | Notes |
|-------|------|-------|
| `Cost_Explorer__AWS__Client` | `billing/service/Cost_Explorer__AWS__Client.py` | Sole boto3 boundary for CE + STS. `client()` is the test seam. Manual `NextPageToken` pagination. `RECORD_TYPE=Usage` filter by default; empty list = all charges. Splits `DataUnavailableException` (CE disabled) from `AccessDeniedException` (IAM missing). Validates all amounts are USD. |
| `Billing__Window__Resolver` | `billing/service/Billing__Window__Resolver.py` | Maps `'last-48h'` / `'week'` / `'mtd'` keywords → `(start, end, granularity)` tuples |
| `Billing__Report__Builder` | `billing/service/Billing__Report__Builder.py` | `ce_client=None` (lazy-inits in `setup()`); `build(start, end, granularity, keyword, metric, group_by_key, top_n, all_charges)` → `Schema__Billing__Report` |

#### CLI commands

Registered as `billing_app` in `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`.

| Command | Description |
|---------|-------------|
| `sg aws billing last-48h` | Daily breakdown, last 2 days |
| `sg aws billing week` | Daily breakdown, last 7 days |
| `sg aws billing mtd` | Month-to-date daily breakdown |
| `sg aws billing window --start YYYY-MM-DD --end YYYY-MM-DD` | Custom date range |
| `sg aws billing summary` | Aggregated service totals: share % + horizontal bars |
| `sg aws billing chart` | Daily totals bar chart: ▲ peak / ▼ low markers, stats footer |

All commands accept `--all-charges` to include credits/refunds/taxes.

#### IAM requirements

`ce:GetCostAndUsage` + `sts:GetCallerIdentity` on `Resource: "*"` (mandatory — CE has no resource-level IAM). `ce:GetDimensionValues` optional.

---

### sg_compute/cli/base/ — EXISTS (v0.2.6)

| Class | Path | Description |
|-------|------|-------------|
| `Spec__CLI__Builder` | `cli/base/Spec__CLI__Builder.py` | Factory; produces a `typer.Typer` with all 8 standard verbs from a `Schema__Spec__CLI__Spec`. Plain class (not Type_Safe). |
| `Spec__CLI__Resolver` | `cli/base/Spec__CLI__Resolver.py` | Auto-pick / prompt / error rule for optional `name`. |
| `Spec__CLI__Errors` | `cli/base/Spec__CLI__Errors.py` | `@spec_cli_errors` decorator + `set_debug()`. Module-level `_DEBUG` flag. |
| `Spec__CLI__Defaults` | `cli/base/Spec__CLI__Defaults.py` | `DEFAULT_REGION`, `DEFAULT_MAX_HOURS=1`, `DEFAULT_TIMEOUT_SEC=600`, `DEFAULT_POLL_SEC=10`, `DEFAULT_EXEC_TIMEOUT=60`. |
| `Schema__Spec__CLI__Spec` | `cli/base/Schema__Spec__CLI__Spec.py` | Per-spec configuration consumed by the builder. Plain class (holds class refs + callables). |
| `Spec__CLI__Renderers__Base` | `cli/base/Spec__CLI__Renderers__Base.py` | Default Rich renderers: `render_list`, `render_info`, `render_create`, `render_delete`, `render_health_probe`, `render_exec_result`. |
| `Schema__CLI__Exec__Result` | `cli/base/schemas/Schema__CLI__Exec__Result.py` | `stdout/stderr: str`, `exit_code: Safe_Int__Exit__Code`, `transport: str`, `duration_ms: int`, `error: str`. |
| `Schema__CLI__Health__Probe` | `cli/base/schemas/Schema__CLI__Health__Probe.py` | `healthy: bool`, `state: str`, `elapsed_ms: int`, `last_error: str`. |

Contract doc: `library/docs/specs/v0.2.6__spec-cli-contract.md`.

### sg_compute/core/spec/Spec__Service__Base — EXISTS (v0.2.6)

| Class | Path | Description |
|-------|------|-------------|
| `Spec__Service__Base` | `core/spec/Spec__Service__Base.py` | Optional base class; default `health/exec/connect_target` impls. Sub-classes override `cli_spec()` + the 5 abstract methods. |

### sg_compute_specs/ollama/ — MIGRATED to Spec__CLI__Builder (v0.2.7)

| Sub-path | Contents |
|----------|----------|
| `cli/Cli__Ollama.py` | Builder-driven; 5 spec extras (`--model/--ami-base/--disk-size/--with-claude/--expose-api`), 3 spec verbs (`models/pull/claude`). Legacy `cli/__init__.py` is empty. |
| `enums/Enum__Ollama__AMI__Base.py` | DLAMI / AL2023 |
| `service/Ollama__AMI__Helper.py` | DLAMI + AL2023 SSM resolvers; `resolve_for_base(region, base)` |
| `service/Ollama__Service.py` | Extends `Spec__Service__Base`; adds `cli_spec()`, `pull_model()`, `claude_session()`, `create_node()` |
| `service/Ollama__User_Data__Builder.py` | Composes `Section__Base/GPU_Verify/Ollama/Agent_Tools/Claude_Launch/Sidecar/Shutdown` |
| `schemas/Schema__Ollama__Create__Request.py` | Adds `ami_base/disk_size_gb/with_claude/expose_api`; default model `gpt-oss:20b`; default instance `g5.xlarge`; default max_hours `1` (D2) |

### sg_compute/platforms/ec2/user_data/ — NEW SECTIONS (v0.2.7)

| Class | Path | Description |
|-------|------|-------------|
| `Section__GPU_Verify` | `user_data/Section__GPU_Verify.py` | `nvidia-smi` check; exits 47 on failure. Empty when `gpu_required=False`. |
| `Section__Ollama` | `user_data/Section__Ollama.py` | Installs Ollama, optional `--expose-api` systemd drop-in, pulls model. |
| `Section__Claude_Launch` | `user_data/Section__Claude_Launch.py` | Boots Claude under tmux; empty when `with_claude=False`. |
| `Section__Agent_Tools` | `user_data/Section__Agent_Tools.py` | Python venv with `requests/httpx/rich`; `/etc/logrotate.d/sg-compute` drop-in. |

### sg_compute/primitives/enums/ — EXISTS

| Class | Values |
|-------|--------|
| `Enum__Spec__Stability` | `STABLE / EXPERIMENTAL / DEPRECATED` |
| `Enum__Spec__Capability` | 12 capabilities (vault-writes, ami-bake, sidecar-attach, remote-shell, metrics, mitm-proxy, iframe-embed, webrtc, container-runtime, browser-automation, llm-inference, design-tool) |
| `Enum__Spec__Nav_Group` | `BROWSERS / DATA / OBSERVABILITY / STORAGE / AI / DEV / OTHER` |
| `Enum__Node__State` | `BOOTING / READY / TERMINATING / TERMINATED / FAILED` |
| `Enum__Pod__State` | `PENDING / RUNNING / STOPPED / FAILED` |
| `Enum__Stack__Creation_Mode` | `FRESH / BAKE_AMI / FROM_AMI` |

### sg_compute/core/spec/ — EXISTS (+ BV2.19: Spec__UI__Resolver)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Spec__Manifest__Entry` | `core/spec/schemas/Schema__Spec__Manifest__Entry.py` | Typed spec catalogue entry; every spec's `manifest.py` exports `MANIFEST: Schema__Spec__Manifest__Entry` |
| `Schema__Spec__Catalogue` | `core/spec/schemas/Schema__Spec__Catalogue.py` | Full catalogue (list of manifest entries) |
| `Spec__Registry` | `core/spec/Spec__Registry.py` | In-memory registry keyed by spec_id |
| `Spec__Resolver` | `core/spec/Spec__Resolver.py` | DAG validation + topological sort for composition |
| `Spec__Loader` | `core/spec/Spec__Loader.py` | Discovers specs from `sg_compute_specs/*/manifest.py` and PEP 621 entry points |
| `Spec__UI__Resolver` | `core/spec/Spec__UI__Resolver.py` | Resolves `sg_compute_specs/{spec_id}/ui/` path; `ui_root_override` for tests |
| `Spec__Readme__Resolver` | `core/spec/Spec__Readme__Resolver.py` | Resolves `sg_compute_specs/{spec_id}/README.md` path; `readme_root_override` for tests — BV__spec-readme-endpoint |

### sg_compute/core/node/ — EXISTS

| Class | Path |
|-------|------|
| `Schema__Node__Info` | `core/node/schemas/Schema__Node__Info.py` |
| `Schema__Node__List` | `core/node/schemas/Schema__Node__List.py` |
| `Schema__Node__Create__Request__Base` | `core/node/schemas/Schema__Node__Create__Request__Base.py` |
| `Schema__Node__Create__Response` | `core/node/schemas/Schema__Node__Create__Response.py` |
| `Schema__Node__Delete__Response` | `core/node/schemas/Schema__Node__Delete__Response.py` |
| `Schema__Stack__Info` (legacy) | `core/node/schemas/Schema__Stack__Info.py` | Kept for spec mapper backwards compat |
| `Node__Manager` | `core/node/Node__Manager.py` | Delegates to Platform; accepts a Fake__Platform in tests |

### sg_compute/core/pod/ — EXISTS (BV2.3 + T2.6b/T2.6c: fully typed)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Pod__Info` | `core/pod/schemas/Schema__Pod__Info.py` | `pod_name: Safe_Str__Pod__Name`, `node_id: Safe_Str__Node__Id`, `image: Safe_Str__Docker__Image`, `state`, `ports: Safe_Str__Message` |
| `Schema__Pod__List` | `core/pod/schemas/Schema__Pod__List.py` | `pods: List[Schema__Pod__Info]` |
| `Schema__Pod__Stats` | `core/pod/schemas/Schema__Pod__Stats.py` | `container: Safe_Str__Pod__Name`, float metrics, `pids: Safe_Int__Pids` |
| `Schema__Pod__Logs__Response` | `core/pod/schemas/Schema__Pod__Logs__Response.py` | `container: Safe_Str__Pod__Name`, `lines: Safe_Int__Log__Lines`, `content: Safe_Str__Log__Content`, `truncated: bool` |
| `Schema__Pod__Stop__Response` | `core/pod/schemas/Schema__Pod__Stop__Response.py` | `name: Safe_Str__Pod__Name`, `stopped/removed: bool`, `error: Safe_Str__Message` |
| `Schema__Pod__Start__Request` | `core/pod/schemas/Schema__Pod__Start__Request.py` | `name: Safe_Str__Pod__Name`, `image: Safe_Str__Docker__Image`, `type_id: Safe_Str__Spec__Id` (ports/env omitted — Type_Safe__Dict not Pydantic-serialisable) |
| `Dict__Pod__Ports` | `core/pod/collections/Dict__Pod__Ports.py` | `Type_Safe__Dict[str→str]` |
| `Dict__Pod__Env` | `core/pod/collections/Dict__Pod__Env.py` | `Type_Safe__Dict[str→str]` |
| `Sidecar__Client` | `core/pod/Sidecar__Client.py` | HTTP adapter for one node's `:19009` sidecar; `list/get/logs/start/stop/remove` |
| `Pod__Manager` | `core/pod/Pod__Manager.py` | Bridge: `node_id → public_ip → Sidecar__Client`; public methods typed `Safe_Str__Node__Id`/`Safe_Str__Pod__Name`; schema construction wraps sidecar values explicitly |

### sg_compute/core/stack/ — EXISTS (placeholders)

`Schema__Stack__Info` (multi-node), `Schema__Stack__List` — shape defined, no manager yet.

### sg_compute/catalog/enums/ — EXISTS (BV2.7)

| Class | Path | Values |
|-------|------|--------|
| `Enum__Stack__Type` | `catalog/enums/Enum__Stack__Type.py` | DOCKER / PODMAN / ELASTIC / OPENSEARCH / PROMETHEUS / VNC / NEKO / FIREFOX |

### sg_compute/core/event_bus/ — EXISTS (BV2.7)

| Class | Path | Description |
|-------|------|-------------|
| `Event__Bus` | `core/event_bus/Event__Bus.py` | `emit/on/off/listener_count/reset`; module-level singleton `event_bus` |
| `Schema__Stack__Event` | `core/event_bus/schemas/Schema__Stack__Event.py` | `type_id/stack_name/region/instance_id/timestamp/detail` |

### sg_compute/image/ — EXISTS (BV2.7)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Image__Stage__Item` | `image/schemas/Schema__Image__Stage__Item.py` | One file/tree to copy into build context |
| `Schema__Image__Build__Request` | `image/schemas/Schema__Image__Build__Request.py` | `image_folder/image_tag/stage_items/dockerfile_name/requirements_name` |
| `Schema__Image__Build__Result` | `image/schemas/Schema__Image__Build__Result.py` | `image_id/image_tags/duration_ms` |
| `Image__Build__Service` | `image/service/Image__Build__Service.py` | Full Docker image build orchestrator (temp dir, stage, `docker_client.images.build`) |
| `List__Str` | `image/collections/List__Str.py` | `expected_type = str` |
| `List__Schema__Image__Stage__Item` | `image/collections/List__Schema__Image__Stage__Item.py` | |

### sg_compute/platforms/ec2/enums/ — EXISTS (BV2.7)

| Class | Path | Values |
|-------|------|--------|
| `Enum__Instance__State` | `platforms/ec2/enums/Enum__Instance__State.py` | pending/running/shutting-down/terminated/stopping/stopped/unknown |

### sg_compute/platforms/ec2/primitives/ — EXISTS (BV2.7)

| Class | Path | Pattern |
|-------|------|---------|
| `Safe_Str__AMI__Id` | `platforms/ec2/primitives/Safe_Str__AMI__Id.py` | `^ami-[0-9a-f]{17}$` |
| `Safe_Str__Instance__Id` | `platforms/ec2/primitives/Safe_Str__Instance__Id.py` | `^i-[0-9a-f]{17}$` |

### sg_compute/platforms/ec2/collections/ — EXISTS (BV2.7)

| Class | Path |
|-------|------|
| `List__Instance__Id` | `platforms/ec2/collections/List__Instance__Id.py` |

### sg_compute/platforms/ — EXISTS

| Class / File | Path | Description |
|--------------|------|-------------|
| `Platform` | `platforms/Platform.py` | Abstract base; defines `create_node`, `list_nodes`, `get_node`, `delete_node` |
| `EC2__Platform` | `platforms/ec2/EC2__Platform.py` | Wraps EC2 helpers; implements `list_nodes`, `get_node`, `delete_node`; `create_node` delegates to spec services |
| `EC2__Launch__Helper` | `platforms/ec2/helpers/EC2__Launch__Helper.py` | (moved from `sg_compute/helpers/aws/`) |
| `EC2__SG__Helper` | `platforms/ec2/helpers/EC2__SG__Helper.py` | |
| `EC2__Tags__Builder` | `platforms/ec2/helpers/EC2__Tags__Builder.py` | |
| `EC2__AMI__Helper` | `platforms/ec2/helpers/EC2__AMI__Helper.py` | |
| `EC2__Instance__Helper` | `platforms/ec2/helpers/EC2__Instance__Helper.py` | |
| `EC2__Stack__Mapper` | `platforms/ec2/helpers/EC2__Stack__Mapper.py` | |
| `Stack__Naming` | `platforms/ec2/helpers/Stack__Naming.py` | |
| `Section__Base` | `platforms/ec2/user_data/Section__Base.py` | (moved from `sg_compute/helpers/user_data/`) |
| `Section__Docker` | `platforms/ec2/user_data/Section__Docker.py` | |
| `Section__Node` | `platforms/ec2/user_data/Section__Node.py` | |
| `Section__Nginx` | `platforms/ec2/user_data/Section__Nginx.py` | |
| `Section__Env__File` | `platforms/ec2/user_data/Section__Env__File.py` | |
| `Section__Shutdown` | `platforms/ec2/user_data/Section__Shutdown.py` | |
| `Section__Sidecar` | `platforms/ec2/user_data/Section__Sidecar.py` | Renders ECR-login + `docker run` block for the host-control sidecar; returns `''` when `registry=''` |
| `Health__Poller` | `platforms/ec2/health/Health__Poller.py` | |
| `Health__HTTP__Probe` | `platforms/ec2/health/Health__HTTP__Probe.py` | |
| `Caller__IP__Detector` | `platforms/ec2/networking/Caller__IP__Detector.py` | |
| `Stack__Name__Generator` | `platforms/ec2/networking/Stack__Name__Generator.py` | |

### sg_compute_specs/ pilot specs — EXISTS

| Spec | Path | Manifest |
|------|------|---------|
| `ollama` | `sg_compute_specs/ollama/` | `manifest.py` — spec_id=`ollama`, stability=EXPERIMENTAL, capabilities=[LLM_INFERENCE] |
| `open_design` | `sg_compute_specs/open_design/` | `manifest.py` — spec_id=`open_design`, stability=EXPERIMENTAL, capabilities=[DESIGN_TOOL, VAULT_WRITES] |
| `docker` | `sg_compute_specs/docker/` | `manifest.py` — spec_id=`docker`, stability=STABLE, capabilities=[CONTAINER_RUNTIME, REMOTE_SHELL, METRICS] |

**`Spec__Loader.load_all()` returns all 3 specs; `Spec__Resolver` validates the empty `extends` graphs.**

### sg_compute_specs/docker/ structure — EXISTS (B3.0)

| Sub-path | Contents |
|----------|----------|
| `enums/Enum__Docker__Stack__State.py` | PENDING/RUNNING/STOPPING/STOPPED/TERMINATING/TERMINATED/UNKNOWN |
| `primitives/Safe_Str__Docker__Stack__Name.py` | regex `^[a-z][a-z0-9\-]{1,62}$` |
| `primitives/Safe_Str__IP__Address.py` | dotted-quad IPv4 |
| `collections/List__Port.py`, `List__Schema__Docker__Info.py` | typed collections |
| `schemas/Schema__Docker__Info.py` | full node view incl. docker_version |
| `schemas/Schema__Docker__Create__Request.py` | stack_name, region, instance_type, from_ami, caller_ip, max_hours, extra_ports |
| `schemas/Schema__Docker__Create__Response.py`, `Delete`, `Health`, `List` | response schemas |
| `service/Docker__AWS__Client.py` | tag constants + `DOCKER_NAMING = Stack__Naming(section_prefix='docker')` |
| `service/Docker__SG__Helper.py` | per-node SG; extra_ports; never `sg-*` prefix |
| `service/Docker__AMI__Helper.py` | AL2023 SSM param lookup |
| `service/Docker__Instance__Helper.py` | list/find/terminate + SSM docker version probe |
| `service/Docker__Launch__Helper.py` | `run_instances` wrapper |
| `service/Docker__Tags__Builder.py` | 6-tag set; `Name` carries `docker-` prefix, never doubled |
| `service/Docker__Stack__Mapper.py` | boto3 dict → Schema__Docker__Info |
| `service/Docker__User_Data__Builder.py` | AL2023 cloud-init; Docker CE + Compose plugin |
| `service/Docker__Health__Checker.py` | polls EC2+SSM+docker version; two-stage |
| `service/Docker__Service.py` | create/list/get/delete/health orchestrator |
| `service/Caller__IP__Detector.py` | checkip.amazonaws.com |
| `service/Random__Stack__Name__Generator.py` | adjective-scientist pairs |
| `api/routes/Routes__Docker__Stack.py` | endpoints at `/api/specs/docker/stack*` |
| `tests/` | 31 unit tests (manifest, user_data_builder, tags_builder, stack_mapper) |
| `ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.{js,html,css}` | Card web component — migrated FV2.6; served at `/api/specs/docker/ui/card/...` |
| `ui/detail/v0/v0.1/v0.1.0/sg-compute-docker-detail.{js,html,css}` | Detail web component — migrated FV2.6; imports use absolute `/ui/` paths |

**All 8 migrated specs** also have `ui/card/` + `ui/detail/` trees (same IFD versioning pattern): `podman`, `vnc`, `neko`, `prometheus`, `opensearch`, `elastic`, `firefox`. `api_site/plugins/` and all per-spec `api_site/components/sp-cli/sg-compute-*-detail/` directories are **deleted** — no longer in the dashboard tree.

### sg_compute/vault/ — EXISTS (BV2.9)

| Class | Path | Description |
|-------|------|-------------|
| `Enum__Vault__Error_Code` | `vault/enums/Enum__Vault__Error_Code.py` | `NO_VAULT_ATTACHED / UNKNOWN_SPEC / DISALLOWED_HANDLE / PAYLOAD_TOO_LARGE` |
| `Safe_Str__Spec__Type_Id` | `vault/primitives/Safe_Str__Spec__Type_Id.py` | spec slug; regex rejects chars outside `[a-z0-9\-_]` |
| `Safe_Str__Stack__Id` | `vault/primitives/Safe_Str__Stack__Id.py` | node stack-id; `_shared` is the cross-node sentinel |
| `Safe_Str__SHA256` | `vault/primitives/Safe_Str__SHA256.py` | 64-char hex |
| `Safe_Str__ISO_Datetime` | `vault/primitives/Safe_Str__ISO_Datetime.py` | ISO-8601 datetime string |
| `Safe_Str__Vault__Handle` | `vault/primitives/Safe_Str__Vault__Handle.py` | handle slug |
| `Safe_Str__Vault__Path` | `vault/primitives/Safe_Str__Vault__Path.py` | vault storage path |
| `Safe_Int__Bytes` | `vault/primitives/Safe_Int__Bytes.py` | non-negative byte count |
| `Schema__Vault__Write__Receipt` | `vault/schemas/Schema__Vault__Write__Receipt.py` | `spec_id/stack_id/handle/bytes_written/sha256/written_at/vault_path` |
| `List__Schema__Vault__Write__Receipt` | `vault/collections/List__Schema__Vault__Write__Receipt.py` | typed collection |
| `List__Vault__Handle` | `vault/collections/List__Vault__Handle.py` | typed collection |
| `Vault__Spec__Writer` | `vault/service/Vault__Spec__Writer.py` | `write/get_metadata/list_spec/delete`; `SHARED_STACK_ID='_shared'`; in-memory dict backing store; `vault_attached=True` in production wiring (T2.4b); real vault I/O deferred to v0.3 |
| `Routes__Vault__Spec` | `vault/api/routes/Routes__Vault__Spec.py` | `PUT/GET/DELETE /vault/spec/{spec_id}/{stack_id}/{handle}`; mounted at `/api/vault` on `Fast_API__Compute` |

**Shims:** `sgraph_ai_service_playwright__cli/vault/` — 11 legacy files replaced with re-export shims for one-release backwards compatibility.

---

### sg_compute/control_plane/ — EXISTS (B4 + BV2.3 + BV2.4)

| Class | Path | Description |
|-------|------|-------------|
| `Fast_API__Compute` | `control_plane/Fast_API__Compute.py` | Mounts `/api/health`, `/api/specs`, `/api/nodes`, `/api/stacks`, `/api/vault`; `StaticFiles` at `/api/specs/{spec_id}/ui`; `/legacy/*` (deprecated SP CLI surface with `X-Deprecated: true` header) |
| `Routes__Ec2__Playwright` | `control_plane/legacy_routes/Routes__Ec2__Playwright.py` | Moved from `fast_api/routes/`; shim left at old path |
| `Routes__Observability` | `control_plane/legacy_routes/Routes__Observability.py` | Moved from `fast_api/routes/`; shim left at old path |
| `Routes__Compute__Health` | `control_plane/routes/Routes__Compute__Health.py` | `GET /api/health`, `GET /api/health/ready` |
| `Routes__Compute__Specs` | `control_plane/routes/Routes__Compute__Specs.py` | `GET /api/specs`, `GET /api/specs/{spec_id}`, `GET /api/specs/{spec_id}/readme` (text/markdown; 404 if absent) |
| `Routes__Compute__Nodes` | `control_plane/routes/Routes__Compute__Nodes.py` | `GET /api/nodes`, `GET /api/nodes/{node_id}`, `POST /api/nodes`, `DELETE /api/nodes/{node_id}`; `POST` calls `EC2__Platform.create_node` (docker spec only; others raise `NotImplementedError`) |
| `Routes__Compute__Pods` | `control_plane/routes/Routes__Compute__Pods.py` | 6 pod endpoints under `/api/nodes/{node_id}/pods/*`; constructor injection of `Pod__Manager` |
| `Routes__Compute__AMIs` | `control_plane/routes/Routes__Compute__AMIs.py` | `GET /api/amis?spec_id=<id>` → `Schema__AMI__List__Response`; delegates to `AMI__Lister` |
| `AMI__Lister` | `core/ami/service/AMI__Lister.py` | Lists AMIs filtered by spec_id; returns `Schema__AMI__List__Response` |
| `Schema__AMI__Info` | `core/ami/schemas/Schema__AMI__Info.py` | `ami_id / name / created_at / state / size_gb` |
| `Schema__AMI__List__Response` | `core/ami/schemas/Schema__AMI__List__Response.py` | `spec_id + amis: List__Schema__AMI__Info` |
| `List__Schema__AMI__Info` | `core/ami/collections/List__Schema__AMI__Info.py` | typed collection |
| `Routes__Compute__Stacks` | `control_plane/routes/Routes__Compute__Stacks.py` | PLACEHOLDER |
| `Exception__AWS__No_Credentials` | `platforms/exceptions/Exception__AWS__No_Credentials.py` | Raised when AWS credentials absent; caught by registered 503 handler in `Fast_API__Compute` |

---

### api_site / dashboard — frontend components — EXISTS (v0.2.1 hotfix)

All dashboard web components live under `sgraph_ai_service_playwright__api_site/components/sg-compute/` (renamed from `sp-cli/` in T3.3b).

| Component | Path (relative to `api_site/`) | Status | Notes |
|-----------|-------------------------------|--------|-------|
| `sg-compute-specs-view` | `components/sg-compute/sg-compute-specs-view/v0/v0.1/v0.1.0/` | COMPLETE | Spec grid; card-body click + keyboard (Enter/Space) dispatch `sp-cli:spec.selected`; `tabindex="0"` + `:focus-visible` ring |
| `sg-compute-spec-detail` | `components/sg-compute/sg-compute-spec-detail/v0/v0.1/v0.1.0/` | COMPLETE | Full manifest panel; README placeholder (backend `GET /api/specs/{id}/readme` TBD); extends lineage text; baked AMIs placeholder |
| `sg-compute-launch-form` | `components/sg-compute/_shared/sg-compute-launch-form/v0/v0.1/v0.1.0/` | COMPLETE | Three-mode selector FRESH/BAKE_AMI/FROM_AMI; CSS-only show/hide; cost preview; `getValues()` returns `creation_mode/ami_id/ami_name`; `validate()` blocks FROM_AMI without AMI |
| `sg-compute-launch-panel` | `components/sg-compute/sg-compute-launch-panel/v0/v0.1/v0.1.0/` | COMPLETE | POST `/api/nodes` with full body including `ami_name`; error/loading states |
| `sg-compute-ami-picker` | `components/sg-compute/_shared/sg-compute-ami-picker/v0/v0.1/v0.1.0/` | COMPLETE | `setSpecId()` fetches `GET /api/amis?spec_id=...` via `apiClient`; loading/error/empty states; dispatches `sg-compute:ami.selected` |
| `sg-compute-compute-view` | `components/sg-compute/sg-compute-compute-view/v0/v0.1/v0.1.0/` | COMPLETE | Nodes list; launch constants from `shared/launch-defaults.js` |
| `sg-compute-nodes-view` | `components/sg-compute/sg-compute-nodes-view/v0/v0.1/v0.1.0/` | COMPLETE | Node cards with pod state; uses canonical `pod_name` / `state` field names |
| `sg-compute-settings-pane` | `components/sg-compute/sg-compute-settings-pane/v0/v0.1/v0.1.0/` | COMPLETE | Settings bus dual-dispatch; WCAG AA contrast |
| `shared/launch-defaults.js` | `shared/launch-defaults.js` | COMPLETE | Single source of truth for `REGIONS`, `INSTANCE_TYPES`, `MAX_HOURS`, `COST_TABLE` |
| `shared/api-client.js` | `shared/api-client.js` | COMPLETE | Shared fetch wrapper used by all components |
| `shared/settings-bus.js` | `shared/settings-bus.js` | COMPLETE | Settings event bus (`getAllDefaults()`) |

**Structural snapshot tests** (all green):
- `tests/ci/test_sg_compute_spec_detail__snapshot.py` — 13 assertions
- `tests/ci/test_sg_compute_ami_picker__snapshot.py` — 17 assertions

---

### sg_compute_specs/vault_publish/ — EXISTS (v0.2.23)

Subdomain-routing cold path for vault-app stacks. Slug registry + Waker Lambda + CloudFront + bootstrap CLI.

#### Spec entry point

| File | Description |
|------|-------------|
| `manifest.py` | `spec_id='vault_publish'`, stability=EXPERIMENTAL, capabilities=[VAULT_WRITES, CONTAINER_RUNTIME, SUBDOMAIN_ROUTING] |
| `version` | Current version string |

#### Primitives and enums (schemas/)

| Class | Path | Pattern |
|-------|------|---------|
| `Safe_Str__Slug` | `schemas/Safe_Str__Slug.py` | `^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$` |
| `Safe_Str__Vault__Key` | `schemas/Safe_Str__Vault__Key.py` | permissive identifier |
| `Enum__Slug__Error_Code` | `schemas/Enum__Slug__Error_Code.py` | `INVALID_FORMAT / RESERVED / TOO_SHORT / TOO_LONG` |
| `Enum__Vault_Publish__State` | `schemas/Enum__Vault_Publish__State.py` | `UNKNOWN / RUNNING / STOPPED / PENDING / STOPPING` |

#### Schemas (schemas/)

| Class | Key fields |
|-------|------------|
| `Schema__Vault_Publish__Entry` | `slug / vault_key / stack_name / fqdn / region / created_at` |
| `Schema__Vault_Publish__Register__Request` | `slug / vault_key / region` |
| `Schema__Vault_Publish__Register__Response` | `slug / fqdn / stack_name / message / elapsed_ms` |
| `Schema__Vault_Publish__Status__Response` | `slug / state / fqdn / vault_url / public_ip / stack_name / elapsed_ms` |
| `Schema__Vault_Publish__Unpublish__Response` | `slug / deleted / stack_name / message / elapsed_ms` |
| `Schema__Vault_Publish__List__Response` | `entries / total / elapsed_ms` |
| `Schema__Vault_Publish__Bootstrap__Request` | `cert_arn / zone / role_arn` — defaults: wildcard ACM ARN + `aws.sg-labs.app` |
| `Schema__Vault_Publish__Bootstrap__Response` | `distribution_id / domain_name / lambda_name / waker_url / zone / created / message / elapsed_ms` |

#### Collections (schemas/)

| Class | Type |
|-------|------|
| `List__Slug` | `Type_Safe__List`, `expected_type = Safe_Str__Slug` |
| `List__Schema__Vault_Publish__Entry` | `Type_Safe__List`, `expected_type = Schema__Vault_Publish__Entry` |

#### Service layer (service/)

| Class | Description |
|-------|-------------|
| `Slug__Registry` | SSM-backed registry at `/sg-compute/vault-publish/slugs/{slug}`. CRUD: `get/put/delete/list_all`. Factory seam `_ssm_factory`. |
| `Slug__Validator` | `validate(slug)` — returns `Enum__Slug__Error_Code` or `None`. Checks format + length + reserved list. |
| `Slug__Routing__Lookup` | DNS/SSM lookup by slug — PROPOSED path for Waker routing; not yet wired. |
| `Reserved__Slugs` | `service/reserved/Reserved__Slugs.py` — hardcoded reserved set (www, api, admin, …). |
| `Vault_Publish__Service` | Orchestrator: `register / unpublish / status / list_slugs / bootstrap`. Five factory seams: `_registry_factory / _vault_app_factory / _cf_client_factory / _deployer_factory / _lambda_client_factory`. |

#### Waker Lambda (waker/)

| Class | Description |
|-------|-------------|
| `Slug__From_Host` | `extract(host) -> Optional[Safe_Str__Slug]`. Parses `<slug>.{SG_AWS__DNS__DEFAULT_ZONE}`. Rejects nested subdomains. |
| `Endpoint__Resolver` | Abstract base — `resolve(slug) / start(instance_id)` |
| `Endpoint__Resolver__EC2` | boto3 `describe_instances` with `tag:StackName` + `tag:StackType=vault-app`. Factory seam `_registry_factory`. |
| `Warming__Page` | `render(slug) -> str` (HTML with auto-refresh meta). `headers() -> dict` (no-cache). `refresh_seconds=10`. |
| `Endpoint__Proxy` | urllib3-based proxy. 5 MB response cap. Returns `{status_code, headers, body}`. |
| `Waker__Handler` | State machine: STOPPED→start+202, PENDING/STOPPING→202, RUNNING+healthy→proxy, UNKNOWN→404. Seams: `_resolver_factory / _proxy_factory`. |
| `Fast_API__Waker` | FastAPI app: catch-all `/{path:path}` + `GET /health`. |
| `lambda_entry.py` | LWA entrypoint: `_app = Fast_API__Waker().setup().app()`. Boots uvicorn on port 8080. |

Waker schemas:
- `waker/schemas/Enum__Instance__State.py` — `RUNNING / STOPPED / PENDING / STOPPING / UNKNOWN`
- `waker/schemas/Schema__Endpoint__Resolution.py` — `slug / instance_id / public_ip / vault_url / state / region`
- `waker/schemas/Schema__Waker__Request_Context.py` — `host / slug / path / method / body`

#### CLI (cli/)

| Command | Description |
|---------|-------------|
| `sg vp register <slug> --vault-key <key>` | Create vault-app stack + register slug in SSM |
| `sg vp unpublish <slug>` | Delete stack + remove slug from SSM |
| `sg vp status <slug>` | Show EC2 state + FQDN |
| `sg vp list` | List all registered slugs (vault keys redacted) |
| `sg vp bootstrap [--cert-arn ARN] [--zone ZONE] [--role-arn ARN]` | Deploy Waker Lambda + create Lambda Function URL + create CF distribution |

Mutation guard: `SG_AWS__CF__ALLOW_MUTATIONS=1` required for bootstrap CF creation.

#### Tests (tests/)

| File | Count | Covers |
|------|-------|--------|
| `test_Safe_Str__Slug.py` | 12 | Slug primitive validation |
| `test_Slug__Registry.py` | 18 | SSM-backed registry in-memory |
| `test_Slug__Validator.py` | 17 | Validator + reserved slugs |
| `test_Vault_Publish__Service.py` | 47 | register/unpublish/status/list_slugs end-to-end |
| `tests/waker/test_Slug__From_Host.py` | 10 | Host parsing |
| `tests/waker/test_Warming__Page.py` | 9 | HTML render + headers |
| `tests/waker/test_Waker__Handler.py` | 12 | State machine paths (all 5 states) |
| `test_Vault_Publish__Service__bootstrap.py` | 24 | Bootstrap end-to-end in-memory |

Total: **149 tests, 0 mocks, 0 patches.**

#### sgraph_ai_service_playwright__cli/aws/cf/ — EXISTS (v0.2.23)

CloudFront CRUD primitive. Sole boto3 boundary for CF. Guarded by `SG_AWS__CF__ALLOW_MUTATIONS=1`.

| Layer | Classes |
|-------|---------|
| Enums | `Enum__CF__Distribution__Status` (Deployed/InProgress), `Enum__CF__Price__Class`, `Enum__CF__Origin__Protocol` |
| Primitives | `Safe_Str__CF__Distribution_Id`, `Safe_Str__CF__Domain_Name`, `Safe_Str__Cert__Arn`, `Safe_Str__CF__Origin_Id` |
| Collections | `List__CF__Alias`, `List__Schema__CF__Distribution`, `List__Schema__CF__Origin` |
| Schemas | `Schema__CF__Distribution`, `Schema__CF__Create__Request`, `Schema__CF__Create__Response`, `Schema__CF__Action__Response`, `Schema__CF__Origin` |
| Service | `CloudFront__Distribution__Builder` (builds DistributionConfig dict), `CloudFront__Origin__Failover__Builder`, `CloudFront__AWS__Client` (list/get/create/disable/delete/wait_deployed) |
| CLI | `Cli__Cf.py` — `sg aws cf distributions list/show/create/disable/delete/wait` |

Test helper: `tests/unit/.../CloudFront__AWS__Client__In_Memory.py` — dict-backed fake, monotonic counter for IDs, `set_deployed()` shortcut. 36 tests.

#### sgraph_ai_service_playwright__cli/aws/lambda_/ — EXISTS (v0.2.23)

Lambda deploy + URL CRUD primitive.

| Layer | Classes |
|-------|---------|
| Enums | `Enum__Lambda__Url__Auth_Type` (NONE/AWS_IAM), `Enum__Lambda__Runtime` (Python 3.11/3.12/3.13), `Enum__Lambda__State` (ACTIVE/INACTIVE/PENDING/FAILED) |
| Primitives | `Safe_Str__Lambda__Name`, `Safe_Str__Lambda__Arn`, `Safe_Str__Lambda__Url` |
| Collections | `List__Schema__Lambda__Function` |
| Schemas | `Schema__Lambda__Function`, `Schema__Lambda__Deploy__Request`, `Schema__Lambda__Deploy__Response`, `Schema__Lambda__Url__Info`, `Schema__Lambda__Action__Response` |
| Service | `Lambda__AWS__Client` (list/get/exists/get_function_url/create_function_url/delete_function_url/delete_function), `Lambda__Deployer` (zip-and-deploy from folder, create or update) |
| CLI | `Cli__Lambda.py` — `sg aws lambda deploy/list/delete` + `url create/show/delete` |

Test helpers: `tests/unit/.../Lambda__AWS__Client__In_Memory.py` + `Lambda__Deployer__In_Memory`. 16 tests.

---

## PROPOSED — does not exist yet

- `Section__Sidecar` user-data composable (BV2.2)
- Per-spec `Spec__Service__Base` common lifecycle base class
- `Node__Identity` — node-id generation/parsing helper
- Remaining legacy specs migrated to `sg_compute_specs/` (phases 3.1–3.8): linux, podman, vnc, neko, prometheus, opensearch, elastic, firefox
- Vault-sourced sidecar API key (follow-on to BV2.9; persistence stubbed)
- Real vault I/O (v0.3 follow-on — `Vault__Spec__Writer` now uses in-memory dict with `vault_attached=True`; persistent vault wiring deferred)

---

## History

| Date | Change |
|------|--------|
| 2026-05-17 | v0.2.23: vault-publish spec — full cold path: slug registry (SSM), `Vault_Publish__Service` (register/unpublish/status/list/bootstrap), `sg_compute_specs/vault_publish/waker/` (Waker Lambda with FastAPI + LWA), `sgraph_ai_service_playwright__cli/aws/cf/` (CloudFront CRUD), `sgraph_ai_service_playwright__cli/aws/lambda_/` (Lambda deploy + URL CRUD). 5 commits (a5de0b1 P1a → 432ba5d P2d). 149 waker+vault-publish tests + 52 CF/Lambda tests — all passing. |
| 2026-05-16 | v0.2.22: `sg aws billing` CLI sub-package — 6 commands, 4 primitives, 4 enums, 4 schemas, 3 collections, 3 service classes, `Cli__Billing.py`. `Cli__Aws.py` updated to register `billing_app`. 6 commits on `claude/plan-billing-view-u0NFG`. |
| 2026-05-05 | T3.3b: `components/sp-cli/` → `components/sg-compute/` directory rename; 28 api_site/ string refs + 45 sg_compute_specs/*/ui/detail/ absolute imports updated; snapshot test COMPONENT_DIR paths corrected; 32/33 CI green |
| 2026-05-05 | T2.1b: `sg-compute-ami-picker.setSpecId()` wired to `GET /api/amis` via `apiClient`; `_populateAmis()` / `_showLoading()` / `_showError()` / `_hidePlaceholder()` added; 17-assertion snapshot test; T2.1 debrief flipped PARTIAL → COMPLETE; frontend component table added to reality doc |
| 2026-05-05 | T2-FE-patch: `ami_name` threaded to POST body; spec-card body click + keyboard wired; README broken link → placeholder; inline styles → CSS classes; `stability||'unknown'`; 13-assertion snapshot test for spec-detail |
| 2026-05-05 | BV2.12: agent_mitmproxy/ deleted (35 files); tests/unit/agent_mitmproxy/ deleted (12 files); ci__agent_mitmproxy.yml deleted; scripts/provision_ec2.py → sg_compute_specs.mitmproxy; shim task deferred (implementations diverged from sg_compute_specs) |
| 2026-05-05 | BV2.11: Lambda packaging cutover — lambda_entry.py + build_request() → sg_compute_specs.playwright.core; sgraph_ai_service_playwright/ deleted (175 files); pyproject.toml updated; 55 test files bulk-updated; 2151 unit tests pass |
| 2026-05-05 | BV2.10: Fast_API__SP__CLI sub-app mounted at /legacy in Fast_API__Compute (auth preserved); ASGI wrapper injects X-Deprecated: true; run_sp_cli.py → Fast_API__Compute; 356 passing under python3.12 |
| 2026-05-05 | FV2.6 (all 8 specs): ui/{card,detail}/v0/v0.1/v0.1.0/ created in sg_compute_specs for docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox; 48 files moved; api_site/plugins/ deleted; detail imports → absolute /ui/ paths; admin/index.html → /api/specs/<id>/ui/ |
| 2026-05-05 | BV2.19: Spec__UI__Resolver + StaticFiles mount at /api/specs/{spec_id}/ui; ui_root_override for tests; sg_compute_specs/*/ui/**/* in pyproject.toml include; 322 tests passing |
| 2026-05-05 | T2.6b (PARTIAL): Pod__Manager public methods typed (Safe_Str__Node__Id/Safe_Str__Pod__Name); Platform + EC2__Platform public methods typed (Safe_Str__Node__Id/Safe_Str__AWS__Region); routes wrap Safe_Str before calling manager/platform; tests updated; schema fields + spec-side deferred to T2.6c |
| 2026-05-05 | T2.4b: vault_attached=True wired in Fast_API__Compute._mount_control_routes; route test prefix fixed to /api/vault; production PUT path unblocked |
| 2026-05-10 | v0.2.7: Ollama wedge — first spec on `Spec__CLI__Builder`. `Cli__Ollama.py` (≤90 LOC + 3 spec extras: `models/pull/claude`); `Ollama__Service` extends `Spec__Service__Base` with `cli_spec()/pull_model()/claude_session()`; new `Ollama__AMI__Helper` (DLAMI default), `Enum__Ollama__AMI__Base`, `Safe_Str__Ollama__Model` primitive; 4 new user-data sections (`Section__GPU_Verify/Section__Ollama/Section__Claude_Launch/Section__Agent_Tools`); model default `qwen2.5-coder:7b` → `gpt-oss:20b`; instance default `g4dn.xlarge` → `g5.xlarge` (R4); 78 new + 45 existing tests passing |
| 2026-05-10 | v0.2.6: `Spec__CLI__Builder` factory + `Spec__CLI__Resolver` + `Spec__CLI__Errors` + `Spec__CLI__Defaults` + `Schema__Spec__CLI__Spec` + `Spec__Service__Base` + 2 result schemas; `Safe_Int__Exit__Code` primitive; CLI contract doc published; 34 new tests; version bumped to v0.2.6 |
| 2026-05-10 | fix(docker): `--disk-size` wired through `sp docker create` legacy path (`sgraph_ai_service_playwright__cli/docker/`) — was already present on `sg-compute spec docker create` |
| 2026-05-05 | BV2.9: sg_compute/vault/ created (13 files); plugin→spec rename; Routes__Vault__Spec mounted at /api/vault on Fast_API__Compute; 11 legacy shims; 313 tests passing |
| 2026-05-05 | BV2.8: object=None → Optional[T] in 10 non-circular spec service files; 7 circular AWS__Client files kept object=None; Optional import added to 17 files |
| 2026-05-05 | BV2.7: 14 new canonical modules in sg_compute (primitives, enums, event_bus, image); 46 spec files import-rewritten; CI guard added; 584 tests passing |
| 2026-05-05 | FV2.8: dashboard confirmed zero `/containers/*` URL references; CSS comment updated to "Pods tab"; BV2.17 (sidecar alias deletion) now unblocked |
| 2026-05-05 | BV2.5: `EC2__Platform.create_node` + `POST /api/nodes`; `Schema__Node__Create__Request__Base` (spec_id/node_name/region/instance_type/max_hours/caller_ip); docker only — others raise `NotImplementedError` |
| 2026-05-05 | BV2.6: `Spec__CLI__Loader` + `Cli__Docker` pilot; `sg-compute spec docker <verb>` routing; 19 new tests |
| 2026-05-05 | BV2.2: `Section__Sidecar` added to `platforms/ec2/user_data/`; wired into all 10 spec `User_Data__Builder` classes; 17 new tests; 553 passing |
| 2026-05-05 | BV2.3: `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 pod collections, `Routes__Compute__Pods` (6 endpoints); 246 tests passing |
| 2026-05-04 | BV2.4: `Routes__Compute__Nodes` constructor injection; `Schema__Node__List` `total`+`region`; `Exception__AWS__No_Credentials` + 503 handler; BV2.1 orphan delete |
| 2026-05-02 | Phase B3.0: docker spec migrated to `sg_compute_specs/docker/`; 31 new tests; `Spec__Loader` now returns 3 specs |
| 2026-05-02 | Phase B2: foundations — primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver/Registry, Node__Manager, manifest.py for ollama+open_design, helpers moved to platforms/ec2/ |
| 2026-05-02 | Phase B1: `ephemeral_ec2/` renamed to `sg_compute/`; pilot specs moved to `sg_compute_specs/`; domain placeholder created |
