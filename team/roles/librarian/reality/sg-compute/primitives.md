# Primitives, Enums, and Core Schemas

**Domain:** `sg-compute/` | **Subarea:** primitives, enums, core (non-pod, non-platform) | **Last updated:** 2026-05-17

Cross-cutting type vocabulary and core abstractions shared across the SG/Compute SDK. Includes spec/node/event-bus/image core packages.

---

## EXISTS

### sg_compute/primitives/

| Class | Path |
|-------|------|
| `Safe_Str__Spec__Id` | `primitives/Safe_Str__Spec__Id.py` |
| `Safe_Str__Node__Id` | `primitives/Safe_Str__Node__Id.py` |
| `Safe_Str__Pod__Name` | `primitives/Safe_Str__Pod__Name.py` |
| `Safe_Str__Stack__Id` | `primitives/Safe_Str__Stack__Id.py` |
| `Safe_Str__Stack__Name` | `primitives/Safe_Str__Stack__Name.py` |
| `Safe_Str__Platform__Name` | `primitives/Safe_Str__Platform__Name.py` |
| `Safe_Str__AWS__Region` | `primitives/Safe_Str__AWS__Region.py` — canonical AWS region — regex `^[a-z]{2}-[a-z]+-\d+$`, allow_empty=True |
| `Safe_Str__SSM__Path` | `primitives/Safe_Str__SSM__Path.py` — SSM parameter path — regex `^[a-zA-Z0-9/_.\-]*$`, allow_empty=True |
| `Safe_Str__Image__Registry` | `primitives/Safe_Str__Image__Registry.py` — Docker/ECR registry hostname — allow_empty=True |
| `Safe_Str__Docker__Image` | `primitives/Safe_Str__Docker__Image.py` — Full image ref (`registry/repo:tag`, `repo@sha256:digest`) — T2.6c |
| `Safe_Str__Log__Content` | `primitives/Safe_Str__Log__Content.py` — Multi-line log text — no regex, 1 MB cap — T2.6c |
| `Safe_Str__Message` | `primitives/Safe_Str__Message.py` — Short human-readable message/error — max 512, no regex |
| `Safe_Int__Hours` | `primitives/Safe_Int__Hours.py` — Node lifetime in hours — min=1, max=168 |
| `Safe_Int__Max__Hours` | `primitives/Safe_Int__Max__Hours.py` — Max node lifetime (0=no auto-terminate) — min=0, max=168 — T2.6c |
| `Safe_Int__Log__Lines` | `primitives/Safe_Int__Log__Lines.py` — Log line count — min=0 — T2.6c |
| `Safe_Int__Pids` | `primitives/Safe_Int__Pids.py` — Container PID count — min=0 — T2.6c |
| `Safe_Int__Exit__Code` | `primitives/Safe_Int__Exit__Code.py` — POSIX exit code — min=-256, max=256 — v0.2.6 |
| `Safe_Str__Ollama__Model` | `primitives/Safe_Str__Ollama__Model.py` — Ollama model ref `^[a-z0-9._\-:]+$`, max=64 — v0.2.7 |

### sg_compute/primitives/enums/

| Class | Values |
|-------|--------|
| `Enum__Spec__Stability` | `STABLE / EXPERIMENTAL / DEPRECATED` |
| `Enum__Spec__Capability` | 12 capabilities (vault-writes, ami-bake, sidecar-attach, remote-shell, metrics, mitm-proxy, iframe-embed, webrtc, container-runtime, browser-automation, llm-inference, design-tool) |
| `Enum__Spec__Nav_Group` | `BROWSERS / DATA / OBSERVABILITY / STORAGE / AI / DEV / OTHER` |
| `Enum__Node__State` | `BOOTING / READY / TERMINATING / TERMINATED / FAILED` |
| `Enum__Pod__State` | `PENDING / RUNNING / STOPPED / FAILED` |
| `Enum__Stack__Creation_Mode` | `FRESH / BAKE_AMI / FROM_AMI` |

### sg_compute/core/spec/ (+ BV2.19: Spec__UI__Resolver)

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Spec__Manifest__Entry` | `core/spec/schemas/Schema__Spec__Manifest__Entry.py` | Typed spec catalogue entry; every spec's `manifest.py` exports `MANIFEST: Schema__Spec__Manifest__Entry` |
| `Schema__Spec__Catalogue` | `core/spec/schemas/Schema__Spec__Catalogue.py` | Full catalogue (list of manifest entries) |
| `Spec__Registry` | `core/spec/Spec__Registry.py` | In-memory registry keyed by spec_id |
| `Spec__Resolver` | `core/spec/Spec__Resolver.py` | DAG validation + topological sort for composition |
| `Spec__Loader` | `core/spec/Spec__Loader.py` | Discovers specs from `sg_compute_specs/*/manifest.py` and PEP 621 entry points |
| `Spec__UI__Resolver` | `core/spec/Spec__UI__Resolver.py` | Resolves `sg_compute_specs/{spec_id}/ui/` path; `ui_root_override` for tests |
| `Spec__Readme__Resolver` | `core/spec/Spec__Readme__Resolver.py` | Resolves `sg_compute_specs/{spec_id}/README.md` path; `readme_root_override` for tests — BV__spec-readme-endpoint |

### sg_compute/core/node/

| Class | Path |
|-------|------|
| `Schema__Node__Info` | `core/node/schemas/Schema__Node__Info.py` |
| `Schema__Node__List` | `core/node/schemas/Schema__Node__List.py` |
| `Schema__Node__Create__Request__Base` | `core/node/schemas/Schema__Node__Create__Request__Base.py` |
| `Schema__Node__Create__Response` | `core/node/schemas/Schema__Node__Create__Response.py` |
| `Schema__Node__Delete__Response` | `core/node/schemas/Schema__Node__Delete__Response.py` |
| `Schema__Stack__Info` (legacy) | `core/node/schemas/Schema__Stack__Info.py` — kept for spec mapper backwards compat |
| `Node__Manager` | `core/node/Node__Manager.py` — delegates to Platform; accepts a Fake__Platform in tests |

### sg_compute/core/stack/ (placeholders)

`Schema__Stack__Info` (multi-node), `Schema__Stack__List` — shape defined, no manager yet.

### sg_compute/catalog/enums/ — BV2.7

| Class | Path | Values |
|-------|------|--------|
| `Enum__Stack__Type` | `catalog/enums/Enum__Stack__Type.py` | DOCKER / PODMAN / ELASTIC / OPENSEARCH / PROMETHEUS / VNC / NEKO / FIREFOX |

### sg_compute/core/event_bus/ — BV2.7

| Class | Path | Description |
|-------|------|-------------|
| `Event__Bus` | `core/event_bus/Event__Bus.py` | `emit/on/off/listener_count/reset`; module-level singleton `event_bus` |
| `Schema__Stack__Event` | `core/event_bus/schemas/Schema__Stack__Event.py` | `type_id/stack_name/region/instance_id/timestamp/detail` |

### sg_compute/image/ — BV2.7

| Class | Path | Description |
|-------|------|-------------|
| `Schema__Image__Stage__Item` | `image/schemas/Schema__Image__Stage__Item.py` | One file/tree to copy into build context |
| `Schema__Image__Build__Request` | `image/schemas/Schema__Image__Build__Request.py` | `image_folder/image_tag/stage_items/dockerfile_name/requirements_name` |
| `Schema__Image__Build__Result` | `image/schemas/Schema__Image__Build__Result.py` | `image_id/image_tags/duration_ms` |
| `Image__Build__Service` | `image/service/Image__Build__Service.py` | Full Docker image build orchestrator (temp dir, stage, `docker_client.images.build`) |
| `List__Str` | `image/collections/List__Str.py` | `expected_type = str` |
| `List__Schema__Image__Stage__Item` | `image/collections/List__Schema__Image__Stage__Item.py` | typed collection |

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`platform.md`](platform.md) — Platform interface and EC2 platform (uses these primitives)
- [`pods.md`](pods.md) — pod management (uses `Safe_Str__Pod__Name`, `Enum__Pod__State`)
- [`specs.md`](specs.md) — spec catalogue (consumes `Schema__Spec__Manifest__Entry`)
- [`cli.md`](cli.md) — CLI builder (consumes `Safe_Int__Exit__Code`)
