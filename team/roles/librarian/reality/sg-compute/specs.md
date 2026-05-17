# Spec Catalogue, Manifests, and Vault

**Domain:** `sg-compute/` | **Subarea:** `sg_compute_specs/` + `sg_compute/vault/` | **Last updated:** 2026-05-17

Pilot specs and their manifests, the v0.2.23 `vault_publish` spec (slug registry + Waker Lambda), and the in-tree `sg_compute/vault/` package that backs the `/api/vault` HTTP surface. CLI-side wrappers for these specs are documented separately — see [`cli.md`](cli.md).

---

## EXISTS

### sg_compute_specs/ pilot specs

| Spec | Path | Manifest |
|------|------|---------|
| `ollama` | `sg_compute_specs/ollama/` | `manifest.py` — spec_id=`ollama`, stability=EXPERIMENTAL, capabilities=[LLM_INFERENCE] |
| `open_design` | `sg_compute_specs/open_design/` | `manifest.py` — spec_id=`open_design`, stability=EXPERIMENTAL, capabilities=[DESIGN_TOOL, VAULT_WRITES] |
| `docker` | `sg_compute_specs/docker/` | `manifest.py` — spec_id=`docker`, stability=STABLE, capabilities=[CONTAINER_RUNTIME, REMOTE_SHELL, METRICS] |

**`Spec__Loader.load_all()` returns all 3 specs; `Spec__Resolver` validates the empty `extends` graphs.**

### sg_compute/core/spec/Spec__Service__Base — v0.2.6

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

### sg_compute_specs/vault_publish/ — EXISTS (v0.2.23)

Subdomain-routing cold path for vault-app stacks. Slug registry + Waker Lambda + CloudFront + bootstrap CLI. CLI surface documented in [`cli.md`](cli.md).

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

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`primitives.md`](primitives.md) — `Schema__Spec__Manifest__Entry`, `Spec__Loader/Resolver/Registry`
- [`platform.md`](platform.md) — `EC2__Platform.create_node` delegates into the per-spec `*__Service` classes here
- [`cli.md`](cli.md) — per-spec CLI surface (`sg-compute spec docker`, `sg vp`, `sg aws cf`, `sg aws lambda`)
- [`pods.md`](pods.md) — pod schemas built atop these spec image refs
