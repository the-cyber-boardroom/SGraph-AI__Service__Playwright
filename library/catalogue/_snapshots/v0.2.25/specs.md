---
title: "Catalogue — Specs"
file: specs.md
shard: specs
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Specs

The `sg_compute_specs/` tree holds the 15 ephemeral-stack specs that share the `Spec__CLI__Builder` (v0.2.6+) contract, the typed `manifest.py` consumed by `Spec__Loader`, and the standard internal folder layout (any subset of `enums/`, `primitives/`, `schemas/`, `collections/`, `service/`, `cli/`, `api/`, `core/`, `docker/`, `ui/`, `tests/`).

- **Contract spec:** [`library/docs/specs/v0.2.6__authoring-a-new-top-level-spec.md`](../docs/specs/v0.2.6__authoring-a-new-top-level-spec.md)
- **Reality (SG/Compute domain):** [`team/roles/librarian/reality/sg-compute/specs.md`](../../team/roles/librarian/reality/sg-compute/specs.md)
- **Loader:** `sg_compute/core/spec/Spec__Loader.py` (returns `Schema__Spec__Manifest__Entry` instances; consumed by `Spec__Registry`)
- **Per-spec UI assets:** `sg_compute_specs/{spec}/ui/{card,detail}/v0/v0.1/v0.1.0/` — mounted under `/api/specs/{spec_id}/ui` by `Spec__UI__Resolver` (BV2.19, 2026-05-05).

---

## Spec Inventory

| Spec | Stability | Capabilities | CLI? | API? | Service? | Tests? | Stack purpose |
|------|-----------|--------------|------|------|----------|--------|---------------|
| `docker` | STABLE | container-runtime, metrics, remote-shell | Y | Y | Y | Y | AL2023 EC2 + Docker CE. Pilot for the `Spec__CLI__Loader` (BV2.6). |
| `elastic` | STABLE | metrics | (legacy `scripts/elastic.py`) | Y | Y | Y | Single-node Elasticsearch + Kibana on EC2. CLI not yet migrated into `sg_compute_specs/elastic/cli/`. |
| `firefox` | EXPERIMENTAL | ami-bake, iframe-embed, mitm-proxy | Y | Y | Y | Y | Firefox (noVNC) + mitmproxy sidecar. CLI in `sgraph_ai_service_playwright__cli/firefox/cli/__init__.py` (552 LOC — `INC-003`). |
| `local_claude` | EXPERIMENTAL | container-runtime, llm-inference | Y | N | Y | Y | Laptop-local Claude → Ollama via LiteLLM sidecar (`docker/local-claude/`). |
| `mitmproxy` | STABLE | mitm-proxy | (no cli/) | Y | (no service/) | Y | mitmproxy-only sidecar spec. Carries Docker assets under `docker/`. The legacy `agent_mitmproxy/` package was deleted in BV2.12 (2026-05-05). |
| `neko` | STABLE | iframe-embed | (legacy `sgraph_ai_service_playwright__cli/neko/cli/`) | Y | Y | Y | Neko WebRTC browser stack. CLI not yet under spec tree. |
| `ollama` | EXPERIMENTAL | llm-inference | Y | N | Y | Y | Ollama GPU stack. First spec on `Spec__CLI__Builder` (v0.2.7, 2026-05-10). Default model `gpt-oss:20b`; default instance `g5.xlarge`. |
| `open_design` | EXPERIMENTAL | design-tool, vault-writes | Y | N | Y | Y | Open-source design tool stack. |
| `opensearch` | STABLE | metrics | (legacy `scripts/opensearch.py`) | Y | Y | Y | Single-node OpenSearch + Dashboards. CLI not yet under spec tree. |
| `playwright` | STABLE | browser-automation, sidecar-attach, vault-writes | Y | (under `core/fast_api/`) | Y | Y | Playwright Chromium service. Detailed in [`service.md`](service.md). Ships as `diniscruz/sg-playwright:{version}`. |
| `podman` | STABLE | container-runtime, metrics, remote-shell | (legacy `scripts/podman.py`) | Y | Y | Y | AL2023 EC2 + Podman. |
| `prometheus` | STABLE | metrics | (legacy `scripts/prometheus.py`) | Y | Y | Y | Prometheus + cAdvisor stack. |
| `vault_app` | EXPERIMENTAL | browser-automation, container-runtime, mitm-proxy, sidecar-attach, vault-writes | Y | N | Y | Y | Vault App stack. CLI is 790 LOC (`Cli__Vault_App.py`) — large but below threshold. Vault TLS / DNS end-to-end shipped 2026-05-15. |
| `vault_publish` | EXPERIMENTAL | container-runtime, subdomain-routing, vault-writes | Y | N | Y | Y | NEW v0.2.23 (2026-05-17): subdomain-routing cold path with slug registry (SSM), Waker Lambda (`waker/` — FastAPI + LWA), CloudFront + Lambda CRUD primitives. 149 waker tests + 52 CF/Lambda tests passing. |
| `vnc` | STABLE | iframe-embed, mitm-proxy | (legacy `scripts/vnc.py`) | Y | Y | Y | Chromium-in-VNC + nginx + mitmproxy stack. |

> **Total: 15 specs.** All have a `manifest.py`; 9 have a `cli/` subfolder; 12 have a `service/`; 13 have an `api/`; all have `tests/`.

---

## The `Spec__CLI__Builder` Contract (v0.2.6+)

Every newly authored spec CLI:

1. Extends `Spec__Service__Base` for its service class.
2. Declares a `Schema__Spec__CLI__Spec` instance (defaults: stack name, region, instance type, max-hours).
3. Calls `Spec__CLI__Builder(...).build()` to generate the standard verb set (`create`, `list`, `info`, `delete`, `wait`).
4. Declares any spec-extra verbs (e.g. `models pull` for ollama, `set-credentials` for firefox).
5. Implements per-spec renderer subclasses of `Spec__CLI__Renderers__Base`.

This collapsed ~150 LOC of boilerplate per spec into ~90 LOC + extras. Pilot was `Cli__Docker`; first user was `Cli__Ollama` (78 new tests).

---

## Manifest Schema (`sg_compute/core/spec/schemas/Schema__Spec__Manifest__Entry.py`)

Every spec's `manifest.py` returns a `Schema__Spec__Manifest__Entry` with:

| Field | Type | Source |
|-------|------|--------|
| `spec_id` | `Safe_Str__Spec__Id` | Stable handle (matches directory name) |
| `display_name` | `Safe_Str__Display__Name` | UI label |
| `icon` | `Safe_Str__Icon` | Emoji or single-char glyph |
| `version` | `Safe_Str__Version` | Read from per-spec `core/version` or local file |
| `stability` | `Enum__Spec__Stability` | `STABLE` / `EXPERIMENTAL` / `DEPRECATED` |
| `boot_seconds_typical` | int | UI hint |
| `capabilities` | `List[Enum__Spec__Capability]` | Cross-spec capability vocabulary |
| `nav_group` | `Enum__Spec__Nav_Group` | UI grouping |

---

## Spec Cross-Refs

| Spec | Reality entry | Other catalogue mention |
|------|---------------|-------------------------|
| `playwright` | [`team/roles/librarian/reality/sg-compute/specs.md`](../../team/roles/librarian/reality/sg-compute/specs.md) + legacy `_archive/v0.1.31/01__playwright-service.md` | [`service.md`](service.md) |
| `vault_publish` | [`team/roles/librarian/reality/sg-compute/specs.md`](../../team/roles/librarian/reality/sg-compute/specs.md) + 2026-05-17 changelog entry | Waker Lambda in [`infra.md`](infra.md) |
| `firefox`, `neko`, `vnc`, `vault_app` | sg-compute/specs.md | UI dashboards in [`team/roles/librarian/reality/sg-compute/pods.md`](../../team/roles/librarian/reality/sg-compute/pods.md) |
| All | [`sg_compute/core/spec/Spec__Loader.py`](../../sg_compute/core/spec/Spec__Loader.py) | Consumed by `Routes__Compute__Specs` |

---

## Open Questions / VERIFYs

- VERIFY: `mitmproxy/` spec lacks both `cli/` and `service/` folders; only `api/`, `core/`, `docker/`, `schemas/`, `tests/`. Confirm whether this is intentional (sidecar-only spec) or an in-progress migration.
- VERIFY: `local_claude/` lacks an `api/` folder despite being a STABLE-pattern CLI spec — its API surface (if any) lives elsewhere (likely under `sg_compute/control_plane/`).
- The 9 specs lacking an in-tree `cli/` subfolder are wired into `Cli__SG.py` via either `scripts/*.py` (legacy) or `sgraph_ai_service_playwright__cli/*/cli/` — see [`cli.md`](cli.md).
