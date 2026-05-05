# Reality — SG/Compute Domain

**Status:** ACTIVE — seeded in phase-1 (B1), foundations added in phase-2 (B2), pod management in BV2.3.
**Last updated:** 2026-05-05 | **Phase:** BV2.3 (pod manager + sidecar client)

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
| `Safe_Str__Platform__Name` | `primitives/Safe_Str__Platform__Name.py` |

### sg_compute/primitives/enums/ — EXISTS

| Class | Values |
|-------|--------|
| `Enum__Spec__Stability` | `STABLE / EXPERIMENTAL / DEPRECATED` |
| `Enum__Spec__Capability` | 12 capabilities (vault-writes, ami-bake, sidecar-attach, remote-shell, metrics, mitm-proxy, iframe-embed, webrtc, container-runtime, browser-automation, llm-inference, design-tool) |
| `Enum__Spec__Nav_Group` | `BROWSERS / DATA / OBSERVABILITY / STORAGE / AI / DEV / OTHER` |
| `Enum__Node__State` | `BOOTING / READY / TERMINATING / TERMINATED / FAILED` |
| `Enum__Pod__State` | `PENDING / RUNNING / STOPPED / FAILED` |
| `Enum__Stack__Creation_Mode` | `FRESH / BAKE_AMI / FROM_AMI` |

### sg_compute/core/spec/ — EXISTS

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Spec__Manifest__Entry` | `core/spec/schemas/Schema__Spec__Manifest__Entry.py` | Typed spec catalogue entry; every spec's `manifest.py` exports `MANIFEST: Schema__Spec__Manifest__Entry` |
| `Schema__Spec__Catalogue` | `core/spec/schemas/Schema__Spec__Catalogue.py` | Full catalogue (list of manifest entries) |
| `Spec__Registry` | `core/spec/Spec__Registry.py` | In-memory registry keyed by spec_id |
| `Spec__Resolver` | `core/spec/Spec__Resolver.py` | DAG validation + topological sort for composition |
| `Spec__Loader` | `core/spec/Spec__Loader.py` | Discovers specs from `sg_compute_specs/*/manifest.py` and PEP 621 entry points |

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

### sg_compute/core/pod/ — EXISTS (BV2.3)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Pod__Info` | `core/pod/schemas/Schema__Pod__Info.py` | `pod_name/node_id/image/state/ports` |
| `Schema__Pod__List` | `core/pod/schemas/Schema__Pod__List.py` | `pods: List[Schema__Pod__Info]` |
| `Schema__Pod__Logs__Response` | `core/pod/schemas/Schema__Pod__Logs__Response.py` | `container/lines/content/truncated` |
| `Schema__Pod__Stop__Response` | `core/pod/schemas/Schema__Pod__Stop__Response.py` | `name/stopped/removed/error` |
| `Schema__Pod__Start__Request` | `core/pod/schemas/Schema__Pod__Start__Request.py` | `name/image/type_id` (ports/env omitted — Type_Safe__Dict not Pydantic-serialisable) |
| `Dict__Pod__Ports` | `core/pod/collections/Dict__Pod__Ports.py` | `Type_Safe__Dict[str→str]` |
| `Dict__Pod__Env` | `core/pod/collections/Dict__Pod__Env.py` | `Type_Safe__Dict[str→str]` |
| `Sidecar__Client` | `core/pod/Sidecar__Client.py` | HTTP adapter for one node's `:19009` sidecar; `list/get/logs/start/stop/remove` |
| `Pod__Manager` | `core/pod/Pod__Manager.py` | Bridge: `node_id → public_ip → Sidecar__Client`; translates sidecar dicts to typed schemas |

### sg_compute/core/stack/ — EXISTS (placeholders)

`Schema__Stack__Info` (multi-node), `Schema__Stack__List` — shape defined, no manager yet.

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

### sg_compute/control_plane/ — EXISTS (B4 + BV2.3 + BV2.4)

| Class | Path | Description |
|-------|------|-------------|
| `Fast_API__Compute` | `control_plane/Fast_API__Compute.py` | Mounts `/api/health`, `/api/specs`, `/api/nodes`, `/api/stacks`; auto-discovers per-spec routes via `Spec__Routes__Loader`; `platform` field injected in tests |
| `Routes__Compute__Health` | `control_plane/routes/Routes__Compute__Health.py` | `GET /api/health`, `GET /api/health/ready` |
| `Routes__Compute__Specs` | `control_plane/routes/Routes__Compute__Specs.py` | `GET /api/specs`, `GET /api/specs/{spec_id}` |
| `Routes__Compute__Nodes` | `control_plane/routes/Routes__Compute__Nodes.py` | `GET /api/nodes`, `GET /api/nodes/{node_id}`, `DELETE /api/nodes/{node_id}`; constructor injection of `Platform` |
| `Routes__Compute__Pods` | `control_plane/routes/Routes__Compute__Pods.py` | 6 pod endpoints under `/api/nodes/{node_id}/pods/*`; constructor injection of `Pod__Manager` |
| `Routes__Compute__Stacks` | `control_plane/routes/Routes__Compute__Stacks.py` | PLACEHOLDER |
| `Exception__AWS__No_Credentials` | `platforms/exceptions/Exception__AWS__No_Credentials.py` | Raised when AWS credentials absent; caught by registered 503 handler in `Fast_API__Compute` |

---

## PROPOSED — does not exist yet

- `EC2__Platform.create_node` + `POST /api/nodes` (BV2.5 — blocks FV2.5 frontend launch flow)
- `Section__Sidecar` user-data composable (BV2.2)
- Per-spec `Spec__Service__Base` common lifecycle base class
- `Node__Identity` — node-id generation/parsing helper
- Remaining legacy specs migrated to `sg_compute_specs/` (phases 3.1–3.8): linux, podman, vnc, neko, prometheus, opensearch, elastic, firefox
- `sg-compute` per-spec CLI subcommands (BV2.6)
- Vault-sourced sidecar API key (BV2.9)

---

## History

| Date | Change |
|------|--------|
| 2026-05-05 | BV2.6: `Spec__CLI__Loader` + `Cli__Docker` pilot; `sg-compute spec docker <verb>` routing; 19 new tests |
| 2026-05-05 | BV2.3: `Pod__Manager`, `Sidecar__Client`, 5 pod schemas, 2 pod collections, `Routes__Compute__Pods` (6 endpoints); 246 tests passing |
| 2026-05-04 | BV2.4: `Routes__Compute__Nodes` constructor injection; `Schema__Node__List` `total`+`region`; `Exception__AWS__No_Credentials` + 503 handler; BV2.1 orphan delete |
| 2026-05-02 | Phase B3.0: docker spec migrated to `sg_compute_specs/docker/`; 31 new tests; `Spec__Loader` now returns 3 specs |
| 2026-05-02 | Phase B2: foundations — primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver/Registry, Node__Manager, manifest.py for ollama+open_design, helpers moved to platforms/ec2/ |
| 2026-05-02 | Phase B1: `ephemeral_ec2/` renamed to `sg_compute/`; pilot specs moved to `sg_compute_specs/`; domain placeholder created |
