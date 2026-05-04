# 01 — v0.2 Architecture (supersedes v0.1.140)

The single source of truth for the SG/Compute architecture as of v0.2.0. **Both Sonnet teams read this in full before starting BV2.x or FV2.x work.**

Predecessor: [`team/comms/briefs/v0.1.140__sg-compute__migration/01__architecture.md`](../v0.1.140__sg-compute__migration/01__architecture.md). That document is now historical — this one replaces it.

---

## 1. Taxonomy (4 nouns)

Same four nouns as v0.1.140; reaffirmed.

| Noun | Definition | Identifier |
|------|-----------|-----------|
| **Node** | One ephemeral compute instance — today an EC2; tomorrow a K8s worker, GCP VM, local Docker host. Always carries `docker + sidecar` baseline. | `node_id` (e.g. `firefox-quiet-fermi-7421`) |
| **Pod** | A Docker / Podman container running inside a Node. Tomorrow: a K8s pod. Belongs to exactly one Node, does not migrate. | `pod_name` (per-node unique) |
| **Spec** | Recipe for what a Node should look like. Versioned per spec. **Currently `extends: []` for all 12** — composition mechanism kept for future. | `spec_id` (kebab-case) |
| **Stack** | Coordinated combination of multiple Nodes. **Reserved noun.** Out of scope for v0.2.x; placeholder routes only. | `stack_id` |

**Vocabulary discipline:** "stack" is **never** used for a single instance. "container" is **never** used for a pod. "plugin" is **never** used for a spec. "type_id" → `spec_id`. Code review found 6 sites in `sp-cli-nodes-view.js` still hardcoding `state === 'running'` — these are tracked in FV2.1 as the state-vocabulary alignment.

---

## 2. The two-package split

Unchanged from v0.1.140. Locked in v0.2.

```
sg-compute (PyPI)                              sg-compute-specs (PyPI)
├── the SDK                                    ├── the catalogue (12 specs)
├── primitives, schemas, enums                 ├── one folder per spec, self-contained
├── Platform abstraction (ec2 today)           ├── depends on sg-compute (>=0.2)
├── Node__Manager, Pod__Manager, Spec__Loader  ├── independently versioned per spec
├── Fast_API__Compute control plane            ├── PEP 621 entry points
├── Fast_API__Host__Control sidecar            └── ships per-spec UI assets (FV2.6)
└── sg-compute CLI dispatcher
```

Both pyproject.toml files live at `sg_compute/pyproject.toml` and `sg_compute_specs/pyproject.toml`. Root `pyproject.toml` retains the legacy `sgraph-ai-service-playwright` name during the dual-write window (deletes in BV2.5).

### What each spec folder must contain (canonical layout)

```
sg_compute_specs/<spec_id>/
├── manifest.py              # MANIFEST: Schema__Spec__Manifest__Entry — typed source of truth
├── version                  # semver — owned by the spec, e.g. 0.1.0
├── README.md                # operator-facing description
├── api/                     # Routes__Spec__<Pascal>__Stack mounted at /api/specs/<spec_id>/...
│   └── routes/
│       └── Routes__Spec__<Pascal>__Stack.py
├── service/                 # spec orchestrator (note: was core/ in original brief; service/ is canonical)
│   ├── <Pascal>__Service.py
│   ├── <Pascal>__User_Data__Builder.py
│   └── <Pascal>__Stack__Mapper.py
├── schemas/                 # Type_Safe schemas
│   ├── Schema__<Pascal>__Create__Request.py
│   ├── Schema__<Pascal>__Create__Response.py
│   ├── Schema__<Pascal>__Info.py
│   └── Schema__<Pascal>__Delete__Response.py
├── enums/                   # OPTIONAL — spec-specific enums
├── primitives/              # OPTIONAL — spec-specific Safe_Str types
├── cli/                     # OPTIONAL — only if the spec has operator-facing CLI verbs
│   └── <spec>_commands.py
├── ui/                      # FV2.6 — per-spec UI components co-located here (not yet populated for any spec)
├── tests/                   # spec-level tests, excluded from wheel
└── (no version/README.md duplication — version file is the single source)
```

**Observed deviations from canonical** (code review):

- `ollama/`, `open_design/`, `mitmproxy/`, `playwright/` deviate. `mitmproxy` and `playwright` manifests are missing `extends`/`soon`/`create_endpoint_path` fields. **BV2.6 normalises all 12 specs to canonical.**
- `Spec__Routes__Loader` only finds `<spec>/api/routes/Routes__<Pascal>__Stack.py`. Three specs advertise paths the loader can't reach — same fix in BV2.6.

---

## 3. Platforms layer

Locked at one platform for v0.2.x: `ec2/`. Future: `_proposed/{k8s,gcp,local}.md` markers stay; no implementation.

```
sg_compute/platforms/
├── Platform.py                       # abstract base
├── ec2/                              # AWS EC2 — only platform implemented today
│   ├── EC2__Platform.py              # implements Platform interface
│   ├── helpers/                      # EC2__Launch__Helper, EC2__SG__Helper, etc.
│   ├── user_data/                    # composable user-data sections
│   ├── health/                       # health pollers
│   └── networking/                   # caller-IP, name generator
└── _proposed/
    ├── k8s.md                        # placeholder
    ├── gcp.md                        # placeholder
    └── local.md                      # placeholder
```

**Status:**
- ✅ `EC2__Platform.list_nodes / get_node / delete_node` are real (use real boto3 via `osbot-aws`).
- ❌ `EC2__Platform.create_node` raises `NotImplementedError`. Spec-specific create runs through each spec's own `Routes__Spec__<Pascal>__Stack` today; the generic `POST /api/nodes { spec_id, ... }` does not work. **BV2.2 fixes this.**

---

## 4. Control plane FastAPI

`sg_compute/control_plane/Fast_API__Compute.py` — orchestrator that lives outside the nodes.

```
GET    /api/health                       # live
GET    /api/health/ready                 # live; reports specs_loaded count
GET    /api/specs                        # live; returns Schema__Spec__Catalogue with 12 entries
GET    /api/specs/{spec_id}              # live
POST   /api/specs/{spec_id}/stack        # live (per-spec route mounted by Spec__Routes__Loader)
GET    /api/specs/{spec_id}/stacks       # live (per-spec)
DELETE /api/specs/{spec_id}/stacks/{id}  # live (per-spec)

GET    /api/nodes                        # live; calls EC2__Platform.list_nodes
GET    /api/nodes/{node_id}              # live; calls EC2__Platform.get_node
DELETE /api/nodes/{node_id}              # live; calls EC2__Platform.delete_node
POST   /api/nodes                        # ❌ NOT live; planned BV2.2 (uses create_node)

GET    /api/pods                         # ❌ stub returns []
POST   /api/nodes/{node_id}/pods         # ❌ NOT live; planned BV2.2
GET    /api/nodes/{node_id}/pods         # ❌ NOT live; planned BV2.2
GET    /api/nodes/{node_id}/pods/{name}  # ❌ NOT live; planned BV2.2
DELETE /api/nodes/{node_id}/pods/{name}  # ❌ NOT live; planned BV2.2

GET    /api/stacks                       # stub returns [] (Stack — multi-node — out of scope for v0.2.x)
POST   /api/stacks                       # ❌ stub
DELETE /api/stacks/{id}                  # ❌ stub
```

**Issues flagged by code review (BV2.2 fixes):**

- `Routes__Compute__Nodes` returns raw dicts (violates "Type_Safe everywhere"); has business logic (violates "routes have no logic"); module-level `_platform()` helper is why the test resorted to `unittest.mock.patch` (violates "no mocks").
- No `Pod__Manager` class. No `Routes__Compute__Pods.py` file.
- No `lambda_handler.py` in `control_plane/` — Lambda packaging parity missing.
- No `/legacy/` mount for backwards-compat with the `Fast_API__SP__CLI` URLs.

---

## 5. Sidecar (host plane) — first-class sub-architecture

Every Node runs a **sidecar**: `Fast_API__Host__Control` from `sg_compute/host_plane/`, served on **port 19009** of the Node's public IP. The sidecar is the inside-the-node API — pod CRUD, shell exec, host metrics.

This is significant enough to deserve its own document — see [`03__sidecar-contract.md`](03__sidecar-contract.md). At a glance:

- **Auth:** X-API-Key header (machine-to-machine) + cookie (browser iframe pattern) + WS handshake via cookie.
- **CORS:** `CORSMiddleware` outermost; reflective origin currently. Hardening pending (open question 2 in README).
- **Auth-free paths:** `/auth/set-cookie-form`, `/auth/set-auth-cookie`, `/host/shell/page`, `/docs-auth`, `/health`.
- **API surface:** `/host/status`, `/host/runtime`, `/host/logs/boot`, `/pods/*` (list/info/logs/start/stop/remove), `/containers/*` (alias kept for legacy callers — BV2.8 deletes), `/shell/execute`, WS `/shell/stream`, `/docs-auth?apikey=...`.

---

## 6. Spec contract — what every spec must provide

A spec is one folder under `sg_compute_specs/<spec_id>/` with the canonical layout from §2. The SDK enforces it by validating the manifest at load time.

### 6.1 The manifest

```python
# sg_compute_specs/firefox/manifest.py
from pathlib import Path

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry import Schema__Spec__Manifest__Entry
from sg_compute.primitives.enums.Enum__Spec__Capability         import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Stability          import Enum__Spec__Stability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group          import Enum__Spec__Nav_Group


def _read_version() -> str:
    return (Path(__file__).parent / 'version').read_text().strip()


MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'firefox',
    display_name         = 'Firefox',
    icon                 = '🦊',
    version              = _read_version(),
    stability            = Enum__Spec__Stability.EXPERIMENTAL,
    nav_group            = Enum__Spec__Nav_Group.BROWSERS,
    capabilities         = [Enum__Spec__Capability.VAULT_WRITES,
                            Enum__Spec__Capability.MITM_PROXY,
                            Enum__Spec__Capability.IFRAME_EMBED],
    boot_seconds_typical = 90,
    extends              = [],                    # always [] in v0.2; reserved for future composition
    soon                 = False,
    create_endpoint_path = '/api/specs/firefox/stack',
)
```

**Required fields:** `spec_id`, `display_name`, `icon`, `version`, `stability`, `nav_group`, `capabilities`, `boot_seconds_typical`, `create_endpoint_path`. **Optional with defaults:** `extends=[]`, `soon=False`. **No raw dicts.** **No Literals.**

### 6.2 The service

`<Spec>__Service.setup() / create_node() / list_nodes() / get_node() / delete_node()`. Plus spec-specific methods (e.g. `health()` for firefox).

**Code review fix BV2.4:** every spec service currently declares dependencies as `: object = None`, silently bypassing Type_Safe. Replace with concrete typed parameters.

### 6.3 Routes

`api/routes/Routes__Spec__<Pascal>__Stack.py` mounts under `/api/specs/<spec_id>/...`. The control plane's `Spec__Routes__Loader` discovers and mounts them on startup.

### 6.4 What the SDK gives the spec for free

- **EC2 launch** with idempotent SG creation, AMI lookup, tag construction, IAM-gated user-data passing.
- **User-data assembly** as composable sections: `Section__Base`, `Section__Docker`, `Section__Node`, `Section__Nginx`, `Section__Env__File`, `Section__Shutdown`, **`Section__Sidecar`** (NEW in v0.2 — installs the host-control image + starts it on `:19009`).
- **Health polling** with retry/timeout.
- **Auto-terminate timer** via `systemd-run` + `InstanceInitiatedShutdownBehavior=terminate`.
- **Naming** (`{spec_id}-{adjective}-{noun}-{4-digits}`).
- **Schema bases** (`Schema__Spec__Create__Request__Base`).
- **CLI scaffolding** — root `sg-compute` provides `node`, `pod`, `spec`, `stack` verbs; per-spec `cli/` is optional.
- **Manifest endpoint** — `GET /api/specs` returns the catalogue.

---

## 7. The Node anatomy (decision: `linux` is dropped)

See [`02__node-anatomy.md`](02__node-anatomy.md) for the rationale. At a glance:

```
Every Node
├── AMI (Amazon Linux 2023 base, or spec-baked AMI)
├── Docker (or Podman) — container runtime, always installed
├── sidecar (Fast_API__Host__Control on :19009) — the host-plane FastAPI
└── spec pods — what makes this Node a "firefox node" or "elastic node"
```

There is no "bare Linux" spec. A node that's just `linux + docker` is identical to a Node baseline with no application pods running yet — not a useful product offering.

---

## 8. Storage specs (NEW in v0.2)

A new category of spec introduced by the v0.27.2 arch brief. First instance: `s3_server` (in `sgraph-ai/SG-Compute__Spec__Storage-S3` — separate repo).

**Storage specs declare** `Enum__Spec__Capability.OBJECT_STORAGE`. They expose a Memory-FS-compatible interface plus their native protocol (S3 SigV4 in this case). They support the operation-mode taxonomy (`FULL_LOCAL / FULL_PROXY / HYBRID / SELECTIVE`) but the SDK doesn't yet generalise it — let `s3_server` validate the pattern.

**Stacks** (multi-node combinations) compose workload-specs + storage-specs. Out of scope for v0.2.x.

---

## 9. Cross-repo policy (NEW in v0.2)

The v0.1.140 brief said "no repo extraction before phase 8". v0.2 amends:

- **Storage specs** are exempt — they may live in their own repos because they bring substantial external dependencies (Memory-FS, AWS SDKs) and have independent release cadences. Pattern set by `s3_server`.
- **All other specs** stay in `sg_compute_specs/` until the global v0.3+ extraction.
- **The SDK** (`sg_compute/`) stays here until v0.3.0.

A spec in its own repo:
- Publishes its own PyPI package (`sg-compute-spec-<name>` convention).
- Declares a `[project.entry-points."sg_compute.specs"]` entry point.
- Is discovered by `Spec__Loader._load_from_entry_points` automatically once installed.
- Owns its own `manifest.py`, `version`, `service/`, `schemas/`, `api/`, `tests/`, `dockerfile/`, `ui/`.

---

## 10. Legacy mapping (status as of v0.2.0 baseline)

| Legacy path | New path | Status at v0.2.0 |
|-------------|----------|------------------|
| `sgraph_ai_service_playwright/` | `sg_compute_specs/playwright/core/` | DUAL-WRITE — legacy load-bearing via `lambda_entry.py` |
| `sgraph_ai_service_playwright__cli/{docker,podman,vnc,neko,prometheus,opensearch,elastic,firefox}/` | `sg_compute_specs/<name>/` | DUAL-WRITE — original copies still load-bearing |
| `sgraph_ai_service_playwright__cli/linux/` | (deleted) | TO DELETE — `linux` dropped intentionally |
| `sgraph_ai_service_playwright__cli/ec2/` | `sg_compute/platforms/ec2/` | PARTIAL — helpers moved; schemas + `Ec2__Service` + `Ec2__AWS__Client` still pinned in legacy AND back-imported by `sg_compute_specs/{vnc,podman,prometheus,elastic}/`. **BV2.4 fixes the dependency cycle.** |
| `sgraph_ai_service_playwright__cli/{aws,core,catalog,image}/` | `sg_compute/<area>/` | NOT MIGRATED — imported by new spec tree. **BV2.4.** |
| `sgraph_ai_service_playwright__cli/vault/` | `sg_compute/vault/` | NOT MIGRATED — no equivalent. **BV2.5.** |
| `sgraph_ai_service_playwright__cli/elastic/lets/` | `sg_compute/observability/lets/` | NOT MIGRATED — LETS briefs `v0.1.31/10..12` still pending. **Deferred to v0.3.** |
| `sgraph_ai_service_playwright__cli/observability/` | `sg_compute/observability/` | PARTIAL. **BV2.5.** |
| `sgraph_ai_service_playwright__cli/lambda/` + `Fast_API__SP__CLI` | `sg_compute/control_plane/` | DUAL-WRITE — both Fast APIs live. **BV2.5.** |
| `sgraph_ai_service_playwright__host/` | `sg_compute/host_plane/` | TO DELETE — orphaned, nothing outside imports it. **BV2.1.** |
| `sgraph_ai_service_playwright__api_site/` | `sg_compute/frontend/` (eventual) | NO MOVE in v0.2.x. **FV2.10 deferred to v0.3.** |
| `agent_mitmproxy/` | `sg_compute_specs/mitmproxy/` | DUAL-WRITE — original load-bearing via dockerfile. **BV2.5.** |

The recommended cleanup order from the legacy code review:

1. `__host/` — DELETE (BV2.1)
2. Tier-1 sub-packages of `__cli/` (`aws`, `core`, `image`, `catalog`, `ec2` schemas, `observability` primitives) — MIGRATE to `sg_compute/` to break the spec→legacy cycle (BV2.4)
3. `__cli/vault/` — MIGRATE (BV2.5)
4. `Fast_API__SP__CLI` + `__cli/deploy/` — MIGRATE into `sg_compute/control_plane/` (BV2.5)
5. Cut over playwright Dockerfile + `lambda_entry.py` to bake from `sg_compute_specs/playwright/core/` (BV2.5)
6. CI guard forbidding `sg_compute*` from importing `sgraph_ai_service_playwright*` (BV2.5)

---

## 11. Open architectural questions (carried into v0.2)

1. **Cookie hardening** (security). Flip `httponly=true` on the auth cookie? — Architect call before BV2.7.
2. **CORS origin lock.** `allow_origin_regex=r".*"` + credentials = vulnerability surface. Architect call before BV2.7.
3. **Per-spec independent PyPI publishing.** Defer to v0.3.0; document the convention now (`sg-compute-spec-<name>`).
4. **Multi-platform routing** (when `local` lands as a second platform). Defer to v0.3+.
5. **UI assets serving from specs** (FV2.6). `GET /api/specs/<id>/ui/<path>` endpoint vs static files served by FastAPI `StaticFiles` mount? Architect + UI Architect call before FV2.6.
6. **`linux` removal** from any UI defaults (linux→podman residue cleanup happened in post-fractal-UI 04.1; verify no v0.2 `extends=['linux']` slipped in).
