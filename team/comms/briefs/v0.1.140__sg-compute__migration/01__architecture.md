# 01 — Architecture

The single source of truth for the SG/Compute migration. **Both Sonnet teams read this in full before starting.**

This document defines:

1. The **taxonomy** (Node / Pod / Spec / Stack)
2. The **two-package split** (`sg-compute` SDK vs `sg-compute-specs` catalogue)
3. The **platforms layer** (today: EC2; future: K8s, GCP, local)
4. The **spec contract** (what every spec must provide; what `sg_compute` provides for free)
5. The **fractal-composition rule** (how specs build on each other)
6. The **legacy-mapping table** (every existing module → its destination in the new tree)

---

## 1. Taxonomy

Four nouns. Each appears in the CLI, the API, the schemas, and the UI.

### Node

A **Node** is a single ephemeral compute instance.

- **Today**: an EC2 instance.
- **Tomorrow**: a Kubernetes worker, a GCP Compute Engine instance, a local Docker host.
- **Always**: has Docker or Podman installed; runs a `host_plane` FastAPI on port 9000; has a node-id, a node-type (the spec it was launched from), a state (BOOTING / READY / TERMINATING), an auto-terminate timer.
- **Naming**: human-readable id like `firefox-quiet-fermi-7421` (spec-name + adjective-noun + 4 digits). The id is the primary key everywhere.

### Pod

A **Pod** is a container (or group of co-located containers) running inside a Node.

- **Today**: one `docker run` or one `podman run` invocation = one pod.
- **Tomorrow**: a Kubernetes pod (one or more containers sharing network and storage).
- **Always**: has a name, an image reference, declared ports, declared env, a state (PENDING / RUNNING / STOPPED), a logs pointer.
- A pod **belongs to exactly one node**. Pods do not migrate.

### Spec

A **Spec** is the recipe that defines what a Node should look like.

- A spec is a **typed manifest** (`Schema__Spec__Manifest`) plus a **service module** that knows how to provision a node from that manifest.
- A spec is **versioned** (per-spec semver, per-spec `version` file).
- A spec can be **composed** of other specs (see §5).
- A spec can be **baked** into an AMI for fast launch, or launched cold (FRESH mode).
- Specs are **discovered** by the SDK at runtime — `sg_compute` walks every installed `*-compute-specs` package and registers its specs in the catalogue.

### Stack

A **Stack** is a coordinated combination of multiple Nodes.

- **Example**: `full-observability-stack` = 1 elastic node + 1 prometheus node + 1 firefox node, in the same VPC, with security groups that let elastic talk to prometheus.
- A stack is launched and torn down as a unit.
- A stack is **NOT** a single instance. The legacy use of "stack" for a single VNC instance was wrong.
- Stacks are **out of scope for the first wave** of this migration — the Stack abstraction lands but only one or two reference stacks are implemented in this phase.

### Vocabulary mapping (legacy → new)

| Legacy term | Where it appears today | New term |
|-------------|------------------------|----------|
| "stack" (single instance) | `Routes__Vnc__Stack`, `sp-cli-stacks-pane`, `Stack__Catalog__Service` | **Node** |
| "instance" | `Schema__Ec2__Instance__Info`, `instance_type` | **Node** (or AWS `instance_type` stays as platform terminology) |
| "container" | `Routes__Host__Containers`, `Container__Runtime__Docker` | **Pod** |
| "plugin" | `Plugin__Registry`, `sp-cli-launcher-pane.PLUGIN_ORDER`, `STATIC.type_id` | **Spec** |
| "type" / "type_id" | `Safe_Str__Plugin__Type_Id` | **Spec id** (`Safe_Str__Spec__Id`) |
| "stack" (multi-instance combination) | not used today | **Stack** (this is the only correct use) |
| "SP" / "sp-cli" | the existing CLI command + `sp-cli-*` web components | **`sg-compute`** (CLI) / **`sg-compute-*`** (UI components — phase 9) |
| "substrate" | (proposed yesterday, never landed) | **platform** |

---

## 2. The two-package split

```
sg-compute                              sg-compute-specs
(PyPI: sg-compute)                      (PyPI: sg-compute-specs)
├── the SDK                             ├── the catalogue
├── helpers, base classes, primitives   ├── one folder per spec
├── platforms abstraction               ├── each spec self-contained
├── control plane FastAPI               ├── depends on sg-compute (>=)
├── host plane FastAPI                  └── independently versioned
├── catalogue loader                       per-spec
├── CLI dispatcher (`sg-compute`)
└── tests (excluded from wheel)

depends on: osbot-utils, osbot-aws,     depends on: sg-compute (>=X.Y),
            osbot-fast-api,                          per-spec runtime libs
            typer, fastapi, pytest                   (only if needed)
```

**Why split?**

- The SDK changes slowly; the catalogue grows fast. Different release cadences.
- Third parties can publish their own catalogues (`acme-compute-specs`, `redteam-compute-specs`) that depend on `sg-compute` and slot into the same dashboard.
- The SDK is testable without any specs installed (mock-spec used by SDK tests).
- A spec author can publish ONE spec as `acme-firefox-spec` later, without rebuilding the whole catalogue.

**Top-level repo layout during the incubation period (this phase):**

```
SGraph-AI__Service__Playwright/                  # this repo
├── sg_compute/                                  # NEW — the SDK
├── sg_compute_specs/                            # NEW — the catalogue
├── sg_compute__tests/                           # tests for sg_compute (mirrors layout)
├── sg_compute_specs__tests/                     # OPTIONAL — only if a spec wants tests
│                                                #   outside its own folder; default is
│                                                #   tests live INSIDE the spec
├── pyproject.toml                               # describes BOTH packages (workspace mode)
│                                                #   OR splits into two pyproject files
│                                                #   per package — see backend plan §3
│
├── sgraph_ai_service_playwright/                # legacy — Playwright FastAPI service
├── sgraph_ai_service_playwright__cli/           # legacy — sp-cli (will migrate per spec)
├── sgraph_ai_service_playwright__host/          # legacy — Host Control Plane (→ sg_compute/host_plane/)
├── sgraph_ai_service_playwright__api_site/      # legacy — Dashboard UI (→ sg_compute/frontend/)
├── agent_mitmproxy/                             # legacy — sibling MITM (→ sg_compute_specs/mitmproxy/)
│
├── docker/                                      # Dockerfiles per image
├── library/                                     # specs / guides / reference (unchanged)
├── team/                                        # role coordination (unchanged)
└── tests/                                       # legacy test tree (unchanged in this phase)
```

The legacy trees keep working. New code goes into `sg_compute*/`. Migration is per-spec, one at a time.

**Inside `sg_compute/` (the SDK):**

```
sg_compute/
├── __init__.py
├── version                          # SDK version, semver
│
├── core/                            # the four-noun runtime
│   ├── node/
│   │   ├── Node__Manager.py         # orchestrates create/list/info/delete on the active platform
│   │   ├── Node__Identity.py        # node-id generation, parsing
│   │   └── schemas/                 # Schema__Node, Schema__Node__Info, Schema__Node__List...
│   ├── pod/
│   │   ├── Pod__Manager.py          # CRUD against host_plane/runtime adapters
│   │   ├── Pod__Runtime.py          # abstract base (was Container__Runtime)
│   │   └── schemas/                 # Schema__Pod, Schema__Pod__Info, ...
│   ├── stack/
│   │   ├── Stack__Manager.py        # multi-node orchestration
│   │   └── schemas/                 # Schema__Stack, ...
│   └── spec/
│       ├── Spec__Loader.py          # discovers specs across installed *-compute-specs packages
│       ├── Spec__Registry.py        # in-memory registry
│       ├── Spec__Resolver.py        # composition / inheritance graph (DAG validation)
│       └── schemas/                 # Schema__Spec__Manifest, Schema__Spec__Catalogue, ...
│
├── platforms/                       # pluggable compute backends (was "substrates")
│   ├── Platform.py                  # abstract base
│   ├── ec2/                         # AWS EC2 — the only platform implemented today
│   │   ├── helpers/                 # was ephemeral_ec2/helpers/aws/
│   │   ├── user_data/               # was ephemeral_ec2/helpers/user_data/
│   │   ├── health/                  # was ephemeral_ec2/helpers/health/
│   │   ├── networking/              # was ephemeral_ec2/helpers/networking/
│   │   └── EC2__Platform.py         # implements Platform interface
│   └── _proposed/
│       ├── k8s.md                   # placeholder — describes what K8s platform would do
│       ├── gcp.md                   # placeholder
│       └── local.md                 # placeholder — local Docker / Podman
│
├── control_plane/                   # the orchestrator FastAPI (was Fast_API__SP__CLI)
│   ├── Fast_API__Compute.py
│   ├── routes/
│   │   ├── Routes__Compute__Nodes.py
│   │   ├── Routes__Compute__Pods.py
│   │   ├── Routes__Compute__Specs.py
│   │   ├── Routes__Compute__Stacks.py
│   │   └── Routes__Compute__Health.py
│   └── lambda_handler.py
│
├── host_plane/                      # runs INSIDE each node (was sgraph_ai_service_playwright__host/)
│   ├── Fast_API__Host.py
│   ├── routes/
│   │   ├── Routes__Host__Pods.py    # was Routes__Host__Containers — RENAMED
│   │   ├── Routes__Host__Shell.py
│   │   └── Routes__Host__Status.py
│   ├── pods/                        # runtime adapters (was containers/)
│   │   ├── Pod__Runtime.py          # base
│   │   ├── Pod__Runtime__Docker.py
│   │   ├── Pod__Runtime__Podman.py
│   │   └── Pod__Runtime__Factory.py
│   ├── shell/                       # allowlisted shell exec (unchanged in scope)
│   └── status/                      # /host/status, /host/runtime
│
├── cli/                             # the `sg-compute` Typer command
│   ├── main.py                      # entry point, sub-command dispatcher
│   ├── node_commands.py
│   ├── pod_commands.py
│   ├── spec_commands.py
│   └── stack_commands.py
│
├── frontend/                        # Dashboard (was sgraph_ai_service_playwright__api_site/)
│   ├── admin/                       # admin shell (was admin/)
│   ├── shared/                      # tokens.css, settings-bus.js, api-client.js
│   ├── components/                  # NEW components live here as sg-compute-*; legacy sp-cli-*
│   │                                # stay until phase 9 cosmetic rename
│   └── (per-spec UI lives under sg_compute_specs/<name>/ui/, mounted dynamically)
│
├── primitives/                      # shared Type_Safe primitives (Safe_Str__*, Enum__*)
├── vault/                           # Vault primitives + per-spec writer
├── catalog/                         # AMI catalogue, spec discovery
├── observability/                   # LETS (log event tracking)
└── tests/                           # SDK tests, mirrors layout (excluded from wheel)
```

**Inside `sg_compute_specs/` (the catalogue):**

```
sg_compute_specs/
├── __init__.py                      # tiny — registers package with Spec__Loader
├── version                          # catalogue-bundle version
│
├── _shared/                         # cross-spec primitives (sparingly populated)
│
├── firefox/                         # one folder per spec
│   ├── manifest.py                  # Schema__Spec__Manifest__Entry — typed source of truth
│   ├── version                      # spec-specific semver (e.g. 0.3.1)
│   ├── README.md                    # operator-facing description
│   ├── api/
│   │   └── Routes__Spec__Firefox.py # mounts at /api/specs/firefox/{node_id}/...
│   ├── core/
│   │   ├── Firefox__Service.py
│   │   └── Firefox__Health.py
│   ├── cli/
│   │   └── firefox_commands.py
│   ├── schemas/                     # one file per Type_Safe class
│   ├── user_data/
│   │   └── Firefox__User_Data__Builder.py
│   ├── ui/                          # web components — co-located with spec
│   │   ├── card/
│   │   │   └── sp-cli-firefox-card.{js,html,css}    # legacy name; rename in phase 9
│   │   └── detail/
│   │       └── sp-cli-firefox-detail.{js,html,css}
│   ├── dockerfile/                  # if the spec ships a container image
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── assets/                      # icon SVG, screenshots
│   └── tests/                       # spec-level tests, excluded from wheel
│
├── docker/
├── podman/
├── elastic/
├── prometheus/
├── opensearch/
├── vnc/
├── neko/
├── playwright/                      # the original FastAPI service folds in here
├── mitmproxy/                       # agent_mitmproxy folds in here
├── ollama/                          # already exists in ephemeral_ec2/stacks/
├── open_design/                     # already exists in ephemeral_ec2/stacks/
├── sg_vault/                        # per the 05/01 ephemeral-infra brief
└── linux/                           # bare Linux terminal
```

---

## 3. Platforms layer

A **Platform** is the implementation of compute provisioning for one cloud / runtime backend. The Platform interface is small and abstract; the EC2 implementation is the reference.

```python
# sg_compute/platforms/Platform.py  (sketch)
class Platform(Type_Safe):
    name: Safe_Str__Platform__Name              # 'ec2' | 'k8s' | 'gcp' | 'local'

    def setup(self) -> 'Platform':
        ...

    def create_node(self, request: Schema__Node__Create__Request,
                    spec: Schema__Spec__Manifest__Entry) -> Schema__Node__Info:
        ...

    def list_nodes(self, region: Safe_Str__Region | None = None) -> Schema__Node__List:
        ...

    def get_node(self, node_id: Safe_Str__Node__Id) -> Schema__Node__Info | None:
        ...

    def delete_node(self, node_id: Safe_Str__Node__Id) -> Schema__Node__Delete__Response:
        ...
```

The `Node__Manager` in `core/node/` delegates to whichever Platform is active. There is exactly **one active platform per process** today; future work may allow per-request routing.

The EC2 platform takes everything that lives in today's `ephemeral_ec2/helpers/aws/` and `helpers/user_data/` etc., reorganises it under `sg_compute/platforms/ec2/`, and presents the `Platform` interface upward. Helpers stay public — spec authors who want low-level control still call them — but the recommended path is `Node__Manager`.

---

## 4. Spec contract

This is what every spec must provide. The SDK enforces it by validating the manifest at load time.

### 4.1 The manifest

`manifest.py` exposes a single module-level constant `MANIFEST: Schema__Spec__Manifest__Entry`. The SDK reads it; nothing else.

```python
# sg_compute_specs/firefox/manifest.py
from pathlib import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry import Schema__Spec__Manifest__Entry
from sg_compute.core.spec.schemas.Enum__Spec__Capability         import Enum__Spec__Capability
from sg_compute.core.spec.schemas.Enum__Spec__Stability          import Enum__Spec__Stability
from sg_compute.core.spec.schemas.Enum__Spec__Nav_Group          import Enum__Spec__Nav_Group


def _read_version() -> str:
    return (Path(__file__).parent / 'version').read_text().strip()


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'firefox',
    display_name         = 'Firefox',
    icon                 = '🦊',
    stability            = Enum__Spec__Stability.EXPERIMENTAL,
    boot_seconds_typical = 90,
    capabilities         = [Enum__Spec__Capability.VAULT_WRITES,
                            Enum__Spec__Capability.MITM_PROXY,
                            Enum__Spec__Capability.IFRAME_EMBED],
    nav_group            = Enum__Spec__Nav_Group.BROWSERS,
    extends              = ['linux', 'docker'],     # fractal composition (see §5)
    soon                 = False,
    version              = _read_version(),
    create_endpoint_path = '/api/specs/firefox',
)
```

Required fields are typed. Optional fields default sensibly. **No raw dicts.**

### 4.2 The service

A spec's `core/<Name>__Service.py` exposes:

```python
class Firefox__Service(Type_Safe):

    def setup(self) -> 'Firefox__Service':
        ...

    def create_node(self,
                    request: Schema__Firefox__Create__Request) -> Schema__Firefox__Create__Response:
        # uses sg_compute.core.node.Node__Manager + per-spec user_data builder
        ...

    def get_node_info(self, node_id: Safe_Str__Node__Id) -> Schema__Firefox__Info | None:
        ...

    def delete_node(self, node_id: Safe_Str__Node__Id) -> Schema__Firefox__Delete__Response:
        ...

    def health(self, node_id: Safe_Str__Node__Id) -> Schema__Firefox__Health:
        # spec-specific health checks (firefox process, mitm, login page)
        ...
```

The first three are the lifecycle minimum (parallel to today's `ephemeral_ec2/brief/05__stack_contract.md`). `health` and any other methods are spec-specific extensions.

### 4.3 Routes

`api/Routes__Spec__<Name>.py` mounts at `/api/specs/<spec_id>/...`. The control plane discovers and mounts these on startup.

### 4.4 What the SDK gives the spec for free

- **EC2 launch** with idempotent SG creation, AMI lookup, tag construction, IAM-gated user-data passing.
- **User-data assembly** as composable sections: `Section__Base`, `Section__Docker`, `Section__Node`, `Section__Nginx`, `Section__Env__File`, `Section__Shutdown`. Specs add their own sections; they don't write `bash` from scratch.
- **Health polling** with retry/timeout, base for "is the EC2 RUNNING?" plus an HTTP probe primitive the spec can compose.
- **Auto-terminate timer** via `systemd-run` + `InstanceInitiatedShutdownBehavior=terminate`.
- **Naming**: adjective-noun-NNNN generator, namespace-scoped to the spec.
- **Schema bases**: `Schema__Spec__Create__Request__Base` (carries `node_name`, `creation_mode`, `ami_id`, `instance_size`, `timeout_minutes`, `region`, `caller_ip`); spec-specific schemas extend it.
- **CLI scaffolding**: `sg-compute spec <name> create / list / info / delete` works without the spec writing any Typer code, by reading the manifest + service.
- **UI manifest**: the catalogue endpoint (`GET /api/specs`) returns every spec's manifest entry; the dashboard renders it without any per-spec frontend logic.

---

## 5. Fractal composition

A spec can declare it extends one or more other specs. The SDK resolves the graph (DAG check, no cycles), merges the user-data sections in topological order, unions capabilities, and presents the result.

### 5.1 Composition rules

- **Manifest**: `extends: ['linux', 'docker']` is a list of spec ids. Order matters for user-data assembly (later extensions can override earlier sections).
- **Capabilities**: union — if `linux` has `[shell-exec]` and `docker` has `[container-runtime]`, then `firefox extends [linux, docker]` has both plus its own.
- **User-data sections**: each spec contributes named sections; sections from later specs replace same-named sections from earlier specs.
- **Schemas**: spec-specific request schemas extend the base; the SDK does not auto-merge schemas (specs own their input contract).
- **Routes**: each spec mounts its own routes at its own path. A composed spec does NOT inherit routes from its parents — composition is for the *boot recipe*, not the API surface.

### 5.2 Validation

`Spec__Resolver` validates at `Spec__Loader.load_all()` time:

- All `extends` ids must exist in the catalogue.
- The graph must be a DAG (cycle detection via depth-first traversal).
- Specs in `extends` must not themselves depend (transitively) on the current spec.

If validation fails, the SDK refuses to start. There is no "warn and continue" — broken composition is a fatal config error.

### 5.3 Example

```
                  ┌──────────────────┐
                  │ linux (base)     │
                  │ - Section__Base  │
                  │ - Section__Shutdown
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │ docker           │
                  │ extends: [linux] │
                  │ - Section__Docker│
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │ firefox          │
                  │ extends: [docker]│
                  │ - Section__Nginx │
                  │ - Section__Mitm  │
                  └──────────────────┘
```

`firefox` user-data assembled = base sections + shutdown + docker install + nginx + mitm.

### 5.4 The "not recursive" rule (re-stated)

A spec's `extends` list cannot mention itself, directly or transitively. The Resolver rejects:

- `firefox.extends = ['firefox']` — direct self-reference.
- `a.extends = ['b']`, `b.extends = ['a']` — cycle of length 2.
- `a.extends = ['b']`, `b.extends = ['c']`, `c.extends = ['a']` — cycle of length 3.

There is no inheritance walking ("super calls"). Composition is **declarative** — you list your parents, the SDK assembles the recipe.

---

## 6. Legacy mapping table

Every existing module → its destination. This is the migration ledger. The backend plan walks through it phase by phase.

### 6.1 SDK destinations (`sg_compute/`)

| Legacy path | New path |
|-------------|----------|
| `ephemeral_ec2/helpers/aws/` | `sg_compute/platforms/ec2/helpers/` |
| `ephemeral_ec2/helpers/user_data/` | `sg_compute/platforms/ec2/user_data/` |
| `ephemeral_ec2/helpers/health/` | `sg_compute/platforms/ec2/health/` |
| `ephemeral_ec2/helpers/networking/` | `sg_compute/platforms/ec2/networking/` |
| `ephemeral_ec2/helpers/schemas/` | `sg_compute/core/node/schemas/` (with renames; "Stack__Info" → "Node__Info") |
| `sgraph_ai_service_playwright__host/` | `sg_compute/host_plane/` |
| `sgraph_ai_service_playwright__host/containers/` | `sg_compute/host_plane/pods/` (renamed) |
| `sgraph_ai_service_playwright__host/fast_api/routes/Routes__Host__Containers.py` | `sg_compute/host_plane/routes/Routes__Host__Pods.py` (renamed) |
| `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` | `sg_compute/control_plane/Fast_API__Compute.py` |
| `sgraph_ai_service_playwright__cli/catalog/` | `sg_compute/catalog/` |
| `sgraph_ai_service_playwright__cli/observability/`, `lets/` | `sg_compute/observability/` |
| `sgraph_ai_service_playwright__cli/vault/` | `sg_compute/vault/` |
| `sgraph_ai_service_playwright__api_site/` | `sg_compute/frontend/` |

### 6.2 Spec destinations (`sg_compute_specs/`)

| Legacy path | New path | Notes |
|-------------|----------|-------|
| `ephemeral_ec2/stacks/ollama/` | `sg_compute_specs/ollama/` | already canonical shape |
| `ephemeral_ec2/stacks/open_design/` | `sg_compute_specs/open_design/` | already canonical shape |
| `sgraph_ai_service_playwright__cli/docker/` | `sg_compute_specs/docker/` | UI moves from `__api_site/plugins/docker/` |
| `sgraph_ai_service_playwright__cli/podman/` | `sg_compute_specs/podman/` | |
| `sgraph_ai_service_playwright__cli/vnc/` | `sg_compute_specs/vnc/` | |
| `sgraph_ai_service_playwright__cli/elastic/` | `sg_compute_specs/elastic/` | |
| `sgraph_ai_service_playwright__cli/prometheus/` | `sg_compute_specs/prometheus/` | |
| `sgraph_ai_service_playwright__cli/opensearch/` | `sg_compute_specs/opensearch/` | |
| `sgraph_ai_service_playwright__cli/neko/` | `sg_compute_specs/neko/` | |
| `sgraph_ai_service_playwright__cli/firefox/` (currently being built) | `sg_compute_specs/firefox/` | absorbs MITM as a sidecar |
| `sgraph_ai_service_playwright__cli/linux/` | `sg_compute_specs/linux/` | already a base spec; promote |
| `sgraph_ai_service_playwright/` (the original FastAPI Playwright service) | `sg_compute_specs/playwright/core/` | folded in as a spec; Lambda packaging stays |
| `agent_mitmproxy/` | `sg_compute_specs/mitmproxy/` | folded in as a spec; addons + admin FastAPI move |

### 6.3 Things that stay where they are (this phase)

- `library/` — specs / guides / reference. Unchanged.
- `team/` — role coordination. Unchanged.
- `docker/` — Dockerfiles. Unchanged in this phase; phase 8 may colocate per-spec Dockerfiles.
- `tests/` (legacy) — unchanged. New tests go inside the new tree.
- `scripts/` — Typer entry-points. Phase 1 doesn't touch them; phase 3+ deprecates the per-spec scripts as their specs migrate.
- `pyproject.toml` — phase 1 keeps the existing `name = "sgraph-ai-service-playwright"`; phase 8 splits into two pyprojects (one per package).

---

## 7. The `sg_compute_specs/<name>/version` file

A plain text file, one line, semver:

```
0.3.1
```

The SDK reads this at manifest-load time; it appears in `Schema__Spec__Manifest__Entry.version` and `GET /api/specs/<id>` responses; the dashboard shows it in the spec detail view. Bump rules:

- **Patch**: bug fix in user-data or service code. No schema change.
- **Minor**: new optional field in request schema; new capability declared; new sub-route.
- **Major**: breaking change to request schema; renamed manifest fields; behavioural change.

When the spec migrates to its own repo (post-phase 9), this file becomes the spec's package version.

---

## 8. Open architectural questions (not blocking phase 1)

Flag these in the relevant team plan; defer decisions until they bind.

1. **Capability vocabulary**. What is the closed set of `Enum__Spec__Capability` values? Initial seed: `vault-writes`, `ami-bake`, `sidecar-attach`, `remote-shell`, `metrics`, `mitm-proxy`, `iframe-embed`, `webrtc`. Architect to lock before phase 3.
2. **Multi-platform routing**. Today exactly one platform is active per process. When `local` (Docker) lands as a second platform, do we run two control-plane instances or one with per-request routing? Backend plan §6.
3. **Spec discovery in installed packages**. Use entry points (`pyproject.toml` `[project.entry-points."sg_compute.specs"]`) or walk `sys.path` for any `*_compute_specs` package? Recommend entry points (PEP 621). Backend plan §3.
4. **Frontend asset loading from specs**. UI components live under `sg_compute_specs/<name>/ui/` — does the dashboard fetch them at runtime via `/api/specs/<id>/ui/<file>`, or does the SDK build a manifest of static URLs at startup? Frontend plan §4.
5. **Stacks (multi-node)**. Out of scope for this wave; brief lands in a follow-up phase. Where do stack definitions live — in the SDK (`sg_compute/core/stack/library/`) or in a third package (`sg-compute-stacks`)? Architect call.
