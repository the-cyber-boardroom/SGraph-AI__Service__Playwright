# Reality — SG/Compute Domain

**Status:** ACTIVE — seeded in phase-1 (B1), foundations added in phase-2 (B2).
**Last updated:** 2026-05-02 | **Phase:** B2 (foundations)

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

### sg_compute/core/pod/ and core/stack/ — EXISTS (placeholders)

`Schema__Pod__Info`, `Schema__Pod__List`, `Schema__Stack__Info` (multi-node), `Schema__Stack__List` — shape defined, no manager yet.

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

**`Spec__Loader.load_all()` returns both specs; `Spec__Resolver` validates the empty `extends` graphs.**

---

## PROPOSED — does not exist yet

- `Fast_API__Compute` control plane (phase 4)
- `sg-compute` CLI command (phase 5)
- `sg_compute/host_plane/` (phase 6 — moves from `sgraph_ai_service_playwright__host/`)
- Per-spec `Spec__Service__Base` common lifecycle base class
- `Node__Identity` — node-id generation/parsing helper
- Remaining legacy specs migrated to `sg_compute_specs/` (phases 3.0–3.8)

---

## History

| Date | Change |
|------|--------|
| 2026-05-02 | Phase B2: foundations — primitives, enums, core schemas, Platform/EC2__Platform, Spec__Loader/Resolver/Registry, Node__Manager, manifest.py for ollama+open_design, helpers moved to platforms/ec2/ |
| 2026-05-02 | Phase B1: `ephemeral_ec2/` renamed to `sg_compute/`; pilot specs moved to `sg_compute_specs/`; domain placeholder created |
