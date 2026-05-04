# Backend Audit — SG/Compute Migration (`v0.1.140__sg-compute__migration`)

**Audit date:** 2026-05-04 22:xx UTC
**Branch:** `dev` @ `v0.1.169` (HEAD `5483738`)
**Brief audited:** `team/comms/briefs/v0.1.140__sg-compute__migration/10__backend-plan.md`
**Auditor scope:** acceptance criteria for backend phases B1, B2, B3.0–B3.7, B4, B5, B6, B7.A, B7.B, B8.

> **Note on B3.8:** the brief lists `firefox` as **B3.8** (most complex, MITM sidecar). The team shipped firefox as **B3.7** (`3dd231b B3.7: add Firefox spec`). All 8 specs in the table (`docker, linux, podman, vnc, neko, prometheus, opensearch, elastic, firefox`) collapse into 8 commits B3.0..B3.7 — but `linux` was **silently dropped**. See B3 gaps.

---

## B1 — Rename `ephemeral_ec2/` → `sg_compute/`; introduce `sg_compute_specs/`

Commit: `1e7978a phase-1: rename ephemeral_ec2 → sg_compute; introduce sg_compute_specs`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sg_compute/` exists, `ephemeral_ec2/` does not | ✅ | `sg_compute/` listed in repo root; `ls ephemeral_ec2` returns NOT-FOUND | |
| `sg_compute_specs/` exists with pilot specs (`ollama`, `open_design`) | ✅ | `sg_compute_specs/ollama/`, `sg_compute_specs/open_design/` | |
| `sg_compute/specs/` removed (only `_shared/` if any) | ✅ | No `sg_compute/specs/` | |
| Per-spec `version` files present | ✅ | `sg_compute_specs/ollama/version=0.1.0`, `sg_compute_specs/open_design/version=0.1.0`, `sg_compute_specs/version=0.1.0` | |
| 8-part brief reads coherently with new naming (no `ephemeral_ec2`) | ✅ | `grep -ln ephemeral` against `sg_compute/brief/*.md` returns nothing | |
| `pyproject.toml` unchanged (package-name flip deferred) | ✅ | `pyproject.toml:2 name="sgraph-ai-service-playwright"` | Flip happened in B8 instead via separate `sg_compute/pyproject.toml` |
| Zero hits of `ephemeral_ec2` in new tree | ✅ | `grep -rln ephemeral_ec2 sg_compute/ sg_compute_specs/ sg_compute__tests/` returns 0 | |

### B1 Gaps
- `sg_compute__tests/stacks/` directory still present (`ollama/`, `open_design/` test subdirs) — should have been moved with the pilot specs to `sg_compute_specs/<name>/tests/`. Cosmetic only; tests pass.

---

## B2 — Foundational base classes and platforms layer

Commit: `0f81038 phase-2: sg-compute foundations`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| All Type_Safe primitives one-class-per-file | ✅ | `sg_compute/primitives/Safe_Str__{Spec__Id, Node__Id, Pod__Name, Stack__Id, Platform__Name}.py` | `Safe_Str__Region`, `Safe_Str__IP__Address`, `Safe_Int__Timeout__Minutes` reuse status not verified in primitives folder |
| Enums one-class-per-file | ✅ | `sg_compute/primitives/enums/Enum__{Spec__Stability, Spec__Capability, Spec__Nav_Group, Node__State, Pod__State, Stack__Creation_Mode}.py` | |
| Closed `Enum__Spec__Capability` set locked before B3 | ⚠ | `sg_compute/primitives/enums/Enum__Spec__Capability.py:5-22` — header comment still says "Architect locks set before phase 3" | 12 values present; no Architect sign-off recorded in commit log |
| Core schemas under `core/{node,pod,spec,stack}/schemas/` | ✅ | `sg_compute/core/{node,pod,spec,stack}/schemas/` exist with Schema__Node, Schema__Pod, Schema__Spec__Manifest__Entry, Schema__Stack etc. | |
| `Platform` interface at `sg_compute/platforms/Platform.py` | ✅ | `sg_compute/platforms/Platform.py` | |
| `EC2__Platform` at `sg_compute/platforms/ec2/EC2__Platform.py` | ✅ | `sg_compute/platforms/ec2/EC2__Platform.py:19` `class EC2__Platform(Platform)` | |
| `helpers/aws/` moved to `platforms/ec2/helpers/` | ✅ | `sg_compute/platforms/ec2/helpers/{EC2__AMI__Helper, EC2__Instance__Helper, EC2__Launch__Helper, EC2__SG__Helper, EC2__Stack__Mapper, EC2__Tags__Builder, Stack__Naming}.py` | |
| `user_data`, `health`, `networking` moved under `platforms/ec2/` | ✅ | `sg_compute/platforms/ec2/{user_data,health,networking}/` populated | |
| `Spec__Loader` at `sg_compute/core/spec/Spec__Loader.py` (dual mode: walk + entry-points) | ✅ | `sg_compute/core/spec/Spec__Loader.py:37-79` `_load_from_package`, `_load_from_entry_points` | |
| `Spec__Resolver` (DAG, cycle detection, topo sort) | ✅ | `sg_compute/core/spec/Spec__Resolver.py` | |
| `Node__Manager` at `core/node/Node__Manager.py` | ✅ | `sg_compute/core/node/Node__Manager.py:19` | |
| Pilot specs (`ollama`, `open_design`) refactored with `manifest.py` + `MANIFEST` | ✅ | `sg_compute_specs/ollama/manifest.py`, `sg_compute_specs/open_design/manifest.py` | |
| Tests for every new class | ✅ | `sg_compute__tests/{core,platforms,primitives}/` mirror structure | Coverage breadth not measured here |
| `Spec__Loader.load_all()` returns 2 specs at end of B2 | ✅ | Per B3.0 commit body: "Spec__Loader now discovers 3 specs (docker, ollama, open_design); updated test_Spec__Loader assertions accordingly" — implies B2 left it at 2 | |
| `Routes__Compute__Specs.list_specs()` placeholder returns catalogue | ⚠ | Built in B4 (`sg_compute/control_plane/routes/Routes__Compute__Specs.py`); not present in B2 commit | Acceptable — brief allowed "placeholder if FastAPI not yet wired" |

### B2 Gaps
- `Pod__Manager` and `Stack__Manager` are NOT created in B2 or anywhere later — Routes__Compute__Pods does not exist; Routes__Compute__Stacks is a hard-coded empty placeholder (`sg_compute/control_plane/routes/Routes__Compute__Stacks.py:21-23`).
- Closed `Enum__Spec__Capability` set: header still asks Architect to lock — no recorded sign-off.
- `EC2__Platform.create_node` is implemented but the brief's specific acceptance ("verified by the existing acceptance test, retargeted to call the new path") wasn't checked; the existing pilot acceptance test must be confirmed manually.

---

## B3.0..B3.7 — Per-spec migration

| Order (brief) | Spec | Commit | Status |
|---|---|---|---|
| B3.0 | docker | `97af231` | ✅ landed |
| B3.1 | **linux** | — | ❌ **MISSING** — never migrated |
| B3.1 (actual) | podman | `2875831` | ✅ landed (numbered as B3.1 by team, displacing `linux`) |
| B3.2 | vnc | `1f86a7b` | ✅ landed |
| B3.3 | neko | `0f35149` | ✅ landed |
| B3.4 | prometheus | `d654425` | ✅ landed |
| B3.5 | opensearch | `b3e94d0` | ✅ landed |
| B3.6 | elastic | `54524ab` | ✅ landed |
| B3.7 (brief: B3.8) | firefox | `3dd231b` | ✅ landed but tagged B3.7 instead of B3.8 |

### Per-spec layout audit (canonical layout requirement: `manifest.py`, `version`, `schemas/`, `core/`, `cli/`, `user_data/`, `api/`, `tests/`)

| Spec | manifest.py | version | schemas | core | cli | user_data | api | tests | Notes |
|---|---|---|---|---|---|---|---|---|---|
| docker     | ✅ | ✅ | ✅ | ❌ (uses `service/`) | ❌ | ❌ (folded into `service/Docker__User_Data__Builder.py`) | ✅ | ✅ | Adds `enums/`, `primitives/`, `collections/` (out of scope additions) |
| podman     | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| vnc        | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| neko       | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| prometheus | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| opensearch | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| elastic    | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |
| firefox    | ✅ | ✅ | ✅ | ❌ (`service/`) | ❌ | ❌ (folded) | ✅ | ✅ | Same shape |

### B3 Gaps
- **`linux` spec was never migrated.** Brief sequenced it as B3.1 ("promote from CLI; becomes a base for fractal composition"). Team renumbered everything down by one and silently skipped it. Consequence: `sg_compute_specs/docker/manifest.py:23` has `extends=[]` instead of `extends=['linux']` — fractal composition base never built.
- **No spec has a `cli/` subdirectory.** Brief required moving `sgraph_ai_service_playwright__cli/<spec>/cli/` → `sg_compute_specs/<spec>/cli/` and registering with the dispatcher (`sg-compute spec docker create / list / info / delete`). None of the 8 specs ship any CLI module under their tree, so the per-spec dispatcher in B5 cannot work.
- **`core/` directory naming.** Plan said `core/`, team used `service/`. Schema-impact only — but the canonical layout in architecture §2 is now diverging.
- **No compatibility shim at the legacy paths.** Plan §3.10 said: "leave a thin re-export at the legacy path that imports from the new location and prints a deprecation warning". Legacy `sgraph_ai_service_playwright__cli/docker/`, `…/podman/`, `…/vnc/`, `…/neko/`, `…/prometheus/`, `…/opensearch/`, `…/elastic/`, `…/firefox/` directories all still contain full original code (not shims). The B3.0 commit message acknowledges: "compatibility shim deferred to a future cleanup phase". This means the migration is a **dual-write** state — two implementations of every spec live side-by-side and can diverge.
- Route classes named `Routes__<Spec>__Stack` rather than the brief's `Routes__Spec__<Spec>` — minor naming drift.
- `create_endpoint_path = '/api/specs/docker/stack'` — the brief's path was `/api/specs/{spec_id}/...`; team appended `/stack` — undocumented choice.

### B3 Out-of-scope additions
- Each spec now has its own `enums/`, `primitives/`, `collections/` subtrees that the brief never asked for. Tradeoff: cleaner per-spec namespacing, more files.

---

## B4 — Control plane FastAPI

Commit: not visible in `git log --grep=B4`; landed without an explicit phase-tagged commit. Debrief commit `76f502b B4 debrief: Fast_API__Compute control plane` exists.

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sg_compute/control_plane/Fast_API__Compute.py` exists | ✅ | `sg_compute/control_plane/Fast_API__Compute.py:25` | |
| Mounts `Routes__Compute__Nodes` at `/api/nodes` | ⚠ | `Fast_API__Compute.py:41` | Endpoint exists but returns hard-coded `{"nodes": [], "total": 0}` (`Routes__Compute__Nodes.py:21-23`) |
| Mounts `Routes__Compute__Pods` at `/api/nodes/{node_id}/pods` | ❌ | `sg_compute/control_plane/routes/` lists only Health/Nodes/Specs/Stacks — no `Routes__Compute__Pods.py` | Brief explicitly required this |
| Mounts `Routes__Compute__Specs` at `/api/specs` | ✅ | `Fast_API__Compute.py:40` | Real impl, returns registry catalogue |
| Mounts `Routes__Compute__Stacks` at `/api/stacks` (placeholder ok) | ⚠ | `Fast_API__Compute.py:42` + placeholder body | Placeholder is fine |
| Mounts `Routes__Compute__Health` at `/api/health/info`, `/api/health/ready` | ✅ | `Fast_API__Compute.py:39` | |
| Discovered per-spec route classes mounted at `/api/specs/{spec_id}/...` | ✅ | `Fast_API__Compute.py:44-48` `_mount_spec_routes` via `Spec__Routes__Loader` | |
| Pure delegation to managers (`Node__Manager`, `Pod__Manager`, `Spec__Registry`, `Stack__Manager`) | ❌ | Routes__Compute__Nodes does NOT call `Node__Manager` (`grep -rn Node__Manager sg_compute/control_plane/` finds only a comment); `Pod__Manager`, `Stack__Manager` classes don't exist anywhere | Routes are stubs, not delegators |
| `sg_compute/control_plane/lambda_handler.py` with Mangum wrapper | ❌ | `find sg_compute -name lambda_handler*` returns only `sg_compute/host_plane/fast_api/lambda_handler.py` | Lambda packaging parity missing for control plane |
| Wire `Fast_API__SP__CLI` to `/legacy/` | ❌ | `grep -rn legacy sg_compute/control_plane/ sgraph_ai_service_playwright__cli/fast_api/` returns nothing | Backwards-compat for `sp-cli` URLs not implemented |
| Integration test hitting every route | ⚠ | `sg_compute__tests/control_plane/` exists; coverage of "every route" not verified | |
| `POST /api/nodes` creates real EC2 instance (or stubbed) | ❌ | `Routes__Compute__Nodes.py:17-26` exposes only `GET /api/nodes` returning empty list. No POST. | Cannot create nodes via control plane |
| `GET /api/nodes/{node_id}` returns state | ❌ | Endpoint not implemented | |
| `DELETE /api/nodes/{node_id}` terminates | ❌ | Endpoint not implemented | |

### B4 Gaps
- Whole node lifecycle (POST, GET-by-id, DELETE) is missing. `Node__Manager` exists in code but is never wired to the control plane. The brief is the most under-delivered phase by far.
- `Routes__Compute__Pods` class missing entirely — `Pod__Manager` not implemented.
- `Stack__Manager` not implemented; placeholder route is acceptable per brief but no class exists.
- No Lambda handler — control plane cannot be deployed via the standard Lambda Web Adapter pattern.
- `/legacy/` mount missing — `sp-cli` compatibility commitment broken.

### B4 Out-of-scope additions
- `Spec__Routes__Loader` — discovers per-spec route classes by convention; reasonable extension of the original brief.

---

## B5 — `sg-compute` CLI

Commit: `ddd3ff8 B5: Add sg-compute CLI (spec / node / pod / stack verbs)`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sg_compute/cli/main.py` (or equivalent) with four top-level verbs | ✅ | `sg_compute/cli/Cli__Compute.py:25-28` adds `spec`, `node`, `pod`, `stack` typer groups | Filename is `Cli__Compute.py` not `main.py` — fine |
| `node_commands.py` exposes `sg-compute node {create, list, info, delete, logs}` | ⚠ | `sg_compute/cli/Cli__Compute__Node.py` exists; need to verify all 5 sub-verbs | B5 commit msg says "list placeholders" — implies create/info/delete/logs may be stubs |
| `spec_commands.py` exposes `sg-compute spec {list, info, validate}` | ⚠ | `Cli__Compute__Spec.py` has `list` and `info` but **no `validate`** | `validate` missing |
| `spec_commands.py` dispatches `sg-compute spec <id> <verb>` to per-spec CLI | ❌ | No dispatcher logic in `Cli__Compute__Spec.py`; per-spec CLI modules don't exist (no `cli/` in any spec) | Major gap — was the whole reason for B3's `cli/` move |
| `pod_commands.py` exposes `sg-compute pod {list, start, stop, logs}` | ⚠ | `Cli__Compute__Pod.py` exists; brief said placeholder OK | |
| `stack_commands.py` placeholder | ✅ | `Cli__Compute__Stack.py` exists | |
| `[project.scripts] sg-compute = "sg_compute.cli.main:app"` | ✅ | `pyproject.toml:38` `sg-compute = "scripts.sg_compute_cli:app"` (root); `sg_compute/pyproject.toml:24` `sg-compute = "sg_compute.cli.Cli__Compute:app"` | Two places, two slightly different paths |
| Per-spec CLI modules registered with dispatcher via manifest | ❌ | No spec has a `cli/` subtree; manifest entries don't reference any | |
| `sg-compute spec docker create --instance-size small` works end-to-end | ❌ | Cannot work — no per-spec dispatcher and no docker `cli/` module | |
| Legacy `sp-cli` not removed | ✅ | `pyproject.toml:37` `sp-cli = "scripts.run_sp_cli:main"` | |

### B5 Gaps
- Per-spec dispatch (`sg-compute spec <id> <verb>`) — the marquee feature of B5 — is not implemented. Bridge depends on B3's missing per-spec `cli/` directories.
- `sg-compute spec validate` missing.

---

## B6 — Move host plane; rename containers→pods

Commit: `c3fc219 B6: move host plane to sg_compute/host_plane/, rename containers→pods`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sgraph_ai_service_playwright__host/` removed | ❌ | Directory still exists at repo root with full content (`Routes__Host__Containers.py`, `Routes__Host__Status.py`, `Routes__Host__Shell.py`) | Was supposed to be `git mv`'d |
| `sg_compute/host_plane/` populated | ✅ | `sg_compute/host_plane/{fast_api,host,pods,shell}/` | |
| `containers/` → `pods/` rename | ✅ | `sg_compute/host_plane/pods/` exists | |
| `Routes__Host__Containers` → `Routes__Host__Pods` | ⚠ | `sg_compute/host_plane/fast_api/routes/Routes__Host__Pods.py` exists but `Routes__Host__Containers.py` ALSO exists in the same directory and is mounted alongside (`Fast_API__Host__Control.py:80`) | Both routes coexist with header note "Container-centric aliases for the UI panel" — out-of-scope retention |
| Path `/containers/*` → `/pods/*` | ⚠ | `/pods/*` exists; `/containers/*` retained as alias | |
| `Container__Runtime` → `Pod__Runtime` | ✅ | `sg_compute/host_plane/pods/service/Pod__Runtime__Factory.py` | |
| `Schema__Container__*` → `Schema__Pod__*`, `container_count` → `pod_count` | ✅ | `sg_compute/host_plane/pods/schemas/Schema__Pod__*.py` | |
| `docker/host-control/Dockerfile` entrypoint updated | ✅ (per commit msg) | Not opened in this audit; commit body claims "Dockerfile updated: COPY sg_compute/, CMD sg_compute.host_plane.fast_api.lambda_handler:_app" | |
| EC2 user-data templates updated | ✅ (per commit msg) | Not verified file-by-file | |
| Tests under `sg_compute__tests/host_plane/` pass | ✅ (per commit msg) | "22 new tests pass; 1848 total passing" | |
| Reality doc updated | ✅ (per commit msg) | Not opened in this audit | |
| Control plane calls new `/pods/...` paths | ⚠ | Control plane has no node-level Pod routes (see B4), so this is moot — nothing in `sg_compute/control_plane/` calls the host plane currently | Cannot verify — surface doesn't exist |

### B6 Gaps
- **`sgraph_ai_service_playwright__host/` not deleted.** Plan said `git mv`; team did `cp` then left the original. Same dual-write trap as B3/B7.
- `Routes__Host__Containers` not actually replaced — kept as a parallel alias inside `sg_compute/host_plane/`. Brief said rename, not alias.

---

## B7.A — `agent_mitmproxy/` → `sg_compute_specs/mitmproxy/`

Commit: `665a308 B7.A: move agent_mitmproxy → sg_compute_specs/mitmproxy/`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `agent_mitmproxy/` removed | ❌ | Top-level `agent_mitmproxy/` still exists with full content (addons, fast_api, schemas, docker, consts, version) | Commit was a **copy**, not a `git mv`, despite the verb in the commit title |
| `sg_compute_specs/mitmproxy/` populated | ✅ | `sg_compute_specs/mitmproxy/{api,core,docker,schemas,tests}/` + `manifest.py` + `version` | |
| `manifest.py` declares `mitmproxy` + capability `mitm-proxy` | ✅ | `sg_compute_specs/mitmproxy/manifest.py` (assumed; entry in `pyproject.toml:23`) | |
| Imports updated across moved tree | ✅ (per commit msg) | "Cross-package callers (Ec2__AWS__Client, Docker__SP__CLI, deploy_code, sp_cli dockerfile) updated to reference the new path" | |
| Tests at `sg_compute_specs/mitmproxy/tests/` pass | ✅ (per commit msg) | "35 tests pass at parity" | |
| `Spec__Loader.load_all()` discovers `mitmproxy` | ✅ | Entry point `mitmproxy = "sg_compute_specs.mitmproxy.manifest"` (`sg_compute_specs/pyproject.toml:23`) | |

### B7.A Gaps
- **Top-level `agent_mitmproxy/` package still exists** at the repo root with the full original implementation. Either delete or convert to a re-export shim. Currently a dual-write state.

---

## B7.B — `sgraph_ai_service_playwright/` → `sg_compute_specs/playwright/`

Commit: `1c9cdb2 B7.B: fold sgraph_ai_service_playwright → sg_compute_specs/playwright/core/`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sgraph_ai_service_playwright/` removed (becomes `sg_compute_specs/playwright/core/`) | ❌ | Both paths exist. Top-level `sgraph_ai_service_playwright/` retained per commit message: "The original sgraph_ai_service_playwright/ package is left intact — the 139 files in sgraph_ai_service_playwright__cli/ continue to use it unchanged as the backward-compat path." | Explicit dual-write — 171 Python files duplicated |
| `sg_compute_specs/playwright/core/` populated | ✅ | `sg_compute_specs/playwright/core/{agentic_fastapi, agentic_fastapi_aws, client, consts, dispatcher, docker, fast_api, metrics, schemas, service, skills}/` | |
| `manifest.py` with `spec_id=playwright`, capability `browser-automation` | ✅ | `sg_compute_specs/playwright/manifest.py:18-29` | Adds `VAULT_WRITES`, `SIDECAR_ATTACH` capabilities (out-of-scope but reasonable) |
| `lambda_entry.py` resolves at new path | ⚠ | `sg_compute_specs/playwright/core/` lists `__init__.py` etc. — `lambda_entry.py` not visible at top of `core/`. Repo root `lambda_entry.py` exists | Lambda still wired via root, not new path |
| pyproject reflects new path | ❌ | `pyproject.toml:8` still says `packages = [{ include = "sgraph_ai_service_playwright" }, { include = "sgraph_ai_service_playwright__cli" }, { include = "sgraph_ai_service_playwright__host" }, ...]` — no reference to `sg_compute_specs.playwright.core` | Lambda Docker build still uses old paths |
| `Spec__Loader.load_all()` discovers `playwright` | ✅ | Entry `playwright = "sg_compute_specs.playwright.manifest"` in `sg_compute_specs/pyproject.toml:28` | |
| 276 original tests still pass | ✅ (per commit msg) | | |

### B7.B Gaps
- Same dual-write situation as B7.A — full 171-file duplicate at the new path. Risk of drift.
- `pyproject.toml` not updated to point at `sg_compute_specs.playwright.core`. The "Lambda deployment of the playwright service still works" acceptance criterion is satisfied only because the **legacy** path still exists, not because the new path is wired up.

---

## B8 — PyPI publish setup

Commit: `b1f810a B8: PyPI build setup — sg-compute and sg-compute-specs wheels`

| Acceptance criterion | Status | Evidence | Notes |
|---|---|---|---|
| `sg_compute/pyproject.toml` exists | ✅ | `sg_compute/pyproject.toml` | name `sg-compute`, version `0.1.0` |
| `sg_compute_specs/pyproject.toml` exists | ✅ | `sg_compute_specs/pyproject.toml` | name `sg-compute-specs`, version `0.1.0` |
| `[project.scripts] sg-compute = "sg_compute.cli.main:app"` on sg-compute only | ✅ | `sg_compute/pyproject.toml:24` `sg-compute = "sg_compute.cli.Cli__Compute:app"` | Path differs from brief but functionally same |
| `[project.entry-points."sg_compute.specs"]` per spec | ✅ | `sg_compute_specs/pyproject.toml:19-31` lists 12 specs | |
| Wheel exclusions: tests, team/, library/ | ⚠ | `tests` excluded (`sg_compute/pyproject.toml:32`, `sg_compute_specs/pyproject.toml:39-41`); `team/`, `library/` not explicitly excluded but `packages.find` includes only `sg_compute*` so they're naturally excluded | |
| `python -m build` produces wheels | ✅ (per commit msg, not re-run here) | Commit body: "python -m build sg_compute/ --wheel" + "python -m build sg_compute_specs/ --wheel" | |
| `pip install` smoke succeeds | ✅ (per commit msg) | "pip install dist/sg_compute-*.whl dist/sg_compute_specs-*.whl" | |
| `sg-compute spec list` works against installed catalogue | ✅ (per commit msg) | "sg-compute spec list  → 12 specs, all versions correct" | |
| No tests in wheels | ✅ (per commit msg) | "unzip -l … | grep tests  → 0 test files shipped" | |
| Spec discovery via PEP 621 entry points | ✅ | `Spec__Loader._load_from_entry_points` (`sg_compute/core/spec/Spec__Loader.py:63-79`) + `sg_compute.specs` group in `sg_compute_specs/pyproject.toml:19` | |

### B8 Gaps
- `sg-compute-specs` lists 12 entry points but the **catalogue does not include `linux`** — this is a downstream consequence of B3 dropping linux, not a B8-specific issue.
- Root `pyproject.toml` was NOT cleaned up — still names `sgraph-ai-service-playwright` and lists legacy packages. Brief item §1 said "Root `pyproject.toml` for `sg-compute`". Team chose to keep three pyproject.toml files (root + sg_compute + sg_compute_specs). Defensible during transition but worth flagging.

---

## Cross-cutting Gaps & Out-of-scope additions

### Gaps that span multiple phases
1. **Dual-write everywhere.** B3 (8 specs), B6 (host plane), B7.A (agent_mitmproxy), B7.B (sgraph_ai_service_playwright) all left the legacy path intact. The brief's intent was `git mv` semantics; the team's pattern was `git cp`. Risk: divergence between old and new code paths until cleanup phases land.
2. **No compatibility shim discipline.** Brief explicitly required deprecation-warning shims at legacy paths (B3 §10). None were created — the legacy paths are still load-bearing.
3. **`linux` spec never migrated** (brief B3.1). Cascades into `extends=[]` on every spec that should have based on linux, breaking the fractal-composition story.
4. **Control plane is half-built** (B4). `Node__Manager` exists but isn't wired; `Pod__Manager` and `Stack__Manager` don't exist; no Lambda handler; no `/legacy/` mount.
5. **Per-spec CLI never built** (B3 + B5). The dispatcher pattern from `sg-compute spec <id> <verb>` cannot work because no spec has a `cli/` subtree.
6. **Architect sign-off on `Enum__Spec__Capability`** never recorded — the file's header still says the set is awaiting Architect lock.

### Out-of-scope additions (team did MORE than the brief asked)
- Per-spec `enums/`, `primitives/`, `collections/` subtrees in every B3 spec — clean namespace but adds shape variance.
- `Spec__Routes__Loader` — discovers per-spec route classes by convention. Reasonable.
- `Routes__Host__Containers` retained as an alias next to `Routes__Host__Pods` to satisfy a UI panel. Documented but contradicts B6's rename intent.
- `sg_compute_specs/playwright/version` symlink to `core/version` for uniform `**/version` glob — pragmatic.
- Multiple new `Cli__Compute__*` files were added during B5 instead of the brief's `*_commands.py` naming.
