# 10 — Backend Sonnet Team: Implementation Plan

**Audience:** the backend Sonnet team
**Prerequisites:** read [`00__README.md`](00__README.md) and [`01__architecture.md`](01__architecture.md) in full. Read [`30__migration-phases.md`](30__migration-phases.md) for cadence and what blocks what.

This plan is sequenced so each phase produces a working green-tests state. Phase 1 lands in one PR; later phases land per-spec or per-component. **One phase per PR. One PR per session.** No big-bang refactors.

Branch naming: `claude/sg-compute-{phase}-{description}-{session-id}`.

---

## Phase 1 — Rename `ephemeral_ec2/` → `sg_compute/`; introduce `sg_compute_specs/`

**Goal:** The new tree exists with the same content as today's `ephemeral_ec2/`, plus an empty `sg_compute_specs/` ready to receive specs. Legacy code is untouched.

**Tasks:**

1. `git mv ephemeral_ec2/ sg_compute/` (preserves history).
2. `git mv ephemeral_ec2__tests/ sg_compute__tests/`.
3. Inside `sg_compute/`, rename `stacks/` → `specs/`. Then **move** the two existing pilot specs out: `git mv sg_compute/specs/ollama/ sg_compute_specs/ollama/`; same for `open_design`.
4. Create empty `sg_compute_specs/__init__.py`. Add `sg_compute_specs/version` containing `0.1.0`.
5. Per-spec `version` files: `sg_compute_specs/ollama/version` = `0.1.0`; `sg_compute_specs/open_design/version` = `0.1.0`.
6. Inside `sg_compute/specs/`, leave only `_shared/` (if anything) — the rest moved to `sg_compute_specs/`. If `specs/` would be empty, delete it.
7. Edit `sg_compute/brief/01__overview.md` through `08__implementation_phases.md`:
   - `s/Ephemeral EC2/SG\/Compute/g` (long form: "Ephemeral Compute" stays as the descriptive subtitle).
   - `s/ephemeral-ec2/sg-compute/g` (PyPI name).
   - `s/ephemeral_ec2/sg_compute/g` (Python import).
   - CLI prefix: `ec2 <stack> <command>` → `sg-compute <verb> <args>` with the four verbs (`node`, `pod`, `spec`, `stack`).
   - Replace all uses of "stack" meaning single-instance with "node". Replace "stack" meaning multi-instance with explicit "stack". Replace "plugin" with "spec".
8. Edit `sg_compute/__init__.py` if it carries the package name.
9. Edit imports across `sg_compute/` and `sg_compute__tests/`: any `from ephemeral_ec2.X` → `from sg_compute.X`.
10. Add a top-level pointer at `team/roles/librarian/reality/index.md` for the new domain `sg-compute/` (placeholder, content lands in phase 2).

**Acceptance criteria:**

- `sg_compute/` and `sg_compute_specs/` exist; `ephemeral_ec2/` does not.
- `pytest sg_compute__tests/` passes (whatever passed in `ephemeral_ec2__tests/` still passes).
- `pytest tests/` (legacy) still passes — unchanged.
- The 8-part brief inside `sg_compute/brief/` reads coherently with the new naming.
- Every grep of `ephemeral_ec2` in the new tree returns zero hits (only history remains).
- `pyproject.toml` is **unchanged in this phase** — the package name flip happens in phase 8.

**Out of scope for phase 1:**

- The Node / Pod / Spec / Stack runtime classes — phase 2.
- The platforms/ rename — phase 2.
- Touching any `sgraph_ai_service_playwright*` package — phase 3+.

**Ship as one PR. Tag `phase-1__sg-compute-rename`.**

---

## Phase 2 — Foundational base classes and the platforms layer

**Goal:** The Node / Pod / Spec / Stack vocabulary exists in code as Type_Safe primitives + base classes + schemas. The EC2 helpers move under `platforms/ec2/` and present the `Platform` interface. Existing pilot specs (`ollama`, `open_design`) are refactored to use the new base classes.

**Tasks:**

1. **Create primitives** under `sg_compute/primitives/` (one file per class):
   - `Safe_Str__Spec__Id.py` — kebab-case spec identifier, validates against `^[a-z][a-z0-9_-]{0,62}$`.
   - `Safe_Str__Node__Id.py` — node identifier (`{spec-id}-{adjective}-{noun}-{4-digits}`).
   - `Safe_Str__Pod__Name.py` — pod (container) name.
   - `Safe_Str__Stack__Id.py` — stack identifier.
   - `Safe_Str__Platform__Name.py` — `'ec2' | 'k8s' | 'gcp' | 'local'` (allowlist primitive).
   - Reuse `Safe_Str__Region`, `Safe_Str__IP__Address`, `Safe_Int__Timeout__Minutes` from existing code if they exist; otherwise create.

2. **Create enums** under `sg_compute/primitives/enums/` (one file per class):
   - `Enum__Spec__Stability.py` — `STABLE / EXPERIMENTAL / DEPRECATED`.
   - `Enum__Spec__Capability.py` — closed set; seed values from architecture §8.1; **lock the closed set with the Architect before phase 3 begins.**
   - `Enum__Spec__Nav_Group.py` — `BROWSERS / DATA / OBSERVABILITY / STORAGE / AI / DEV / OTHER`.
   - `Enum__Node__State.py` — `BOOTING / READY / TERMINATING / TERMINATED / FAILED`.
   - `Enum__Pod__State.py` — `PENDING / RUNNING / STOPPED / FAILED`.
   - `Enum__Stack__Creation_Mode.py` — `FRESH / BAKE_AMI / FROM_AMI` (move from existing `sgraph_ai_service_playwright__cli` if landed; otherwise create).

3. **Create core schemas** (one Type_Safe class per file under `sg_compute/core/{node,pod,spec,stack}/schemas/`):
   - `Schema__Node`, `Schema__Node__Info`, `Schema__Node__List`, `Schema__Node__Create__Request__Base`, `Schema__Node__Create__Response`, `Schema__Node__Delete__Response`.
   - `Schema__Pod`, `Schema__Pod__Info`, `Schema__Pod__List`, `Schema__Pod__Logs__Response`, `Schema__Pod__Start__Request`.
   - `Schema__Spec__Manifest__Entry`, `Schema__Spec__Catalogue`.
   - `Schema__Stack`, `Schema__Stack__Info`, `Schema__Stack__List` (placeholders — multi-node stacks land in a later phase).

4. **Create the `Platform` interface** at `sg_compute/platforms/Platform.py` per architecture §3 sketch.

5. **Move `sg_compute/helpers/aws/` → `sg_compute/platforms/ec2/helpers/`** and create `sg_compute/platforms/ec2/EC2__Platform.py` implementing the `Platform` interface. Helpers stay public.

6. **Move user_data / health / networking** from `sg_compute/helpers/{user_data,health,networking}/` → `sg_compute/platforms/ec2/{user_data,health,networking}/`. The non-AWS-specific bits (e.g. `Section__Shutdown.py`'s systemd-run logic) stay where they are if they truly are platform-agnostic; otherwise move under `platforms/ec2/`.

7. **Create the `Spec__Loader`** at `sg_compute/core/spec/Spec__Loader.py`:
   - Reads PEP 621 entry points group `sg_compute.specs` from installed packages.
   - For this phase, also walks `sg_compute_specs/` directly (since not yet PyPI-published).
   - Imports each spec's `manifest.py`, validates the `MANIFEST` constant against `Schema__Spec__Manifest__Entry`, populates a `Spec__Registry`.
   - Calls `Spec__Resolver` to validate the composition graph (DAG, no cycles).

8. **Create the `Spec__Resolver`** at `sg_compute/core/spec/Spec__Resolver.py`:
   - DFS over `extends` lists; raise on cycle.
   - Topological sort for user-data section assembly.

9. **Refactor `ollama` and `open_design` pilot specs** to use the new base classes:
   - Each gets a real `manifest.py` with a `MANIFEST` constant.
   - `version` file present.
   - Service classes inherit from common bases where applicable; they don't have to (see architecture §4 — composition over inheritance), but the SDK should provide a `Spec__Service__Base` for the common lifecycle methods.

10. **Create the `Node__Manager`** at `sg_compute/core/node/Node__Manager.py`:
    - Constructor takes a `Platform` instance.
    - Methods delegate to the platform: `create_node`, `list_nodes`, `get_node`, `delete_node`.
    - The orchestrator FastAPI (phase 4) calls this; today's helpers are still accessible directly for spec authors who want low-level control.

11. **Tests** — every new class gets a unit test under `sg_compute__tests/` mirroring the layout. **No mocks; no patches.** Use the existing in-memory test composition pattern.

12. **Reality doc** — start migrating the `sg-compute/` domain in `team/roles/librarian/reality/sg-compute/index.md` (part of phase 2's commit). Pilot the migration with whatever lands here.

**Acceptance criteria:**

- All Type_Safe classes follow the one-class-per-file rule. No Pydantic. No Literals.
- `pytest sg_compute__tests/` still passes — every new class has a test.
- `Spec__Loader.load_all()` returns 2 specs (`ollama`, `open_design`) at end of phase, with composition graph validated.
- `EC2__Platform.create_node(...)` produces the same instance as `ephemeral_ec2/stacks/open_design/service/Open_Design__Service.create_stack(...)` did before — verified by the existing acceptance test, retargeted to call the new path.
- `Routes__Compute__Specs.list_specs()` (placeholder if FastAPI not yet wired) returns the 2-spec catalogue.

**Ship as one PR. Tag `phase-2__sg-compute-foundations`.**

---

## Phase 3 — Migrate one legacy spec as proof-of-contract

**Goal:** The simplest legacy spec (`docker`) moves from `sgraph_ai_service_playwright__cli/docker/` to `sg_compute_specs/docker/`, using the new helpers. This validates that the SDK's contract is sufficient to host real specs. Future phases (3.1, 3.2, ...) repeat for each remaining legacy spec.

**Tasks for the docker pilot (3.0):**

1. Create `sg_compute_specs/docker/` with the canonical layout from architecture §2.
2. Write `manifest.py` with a `MANIFEST` constant (spec_id `docker`, stability stable, extends `['linux']`).
3. `version` file = `0.1.0` (or read current `sgraph_ai_service_playwright__cli/docker/version` if it has one).
4. Move schemas: `sgraph_ai_service_playwright__cli/docker/schemas/Schema__Docker__*.py` → `sg_compute_specs/docker/schemas/`. Update imports.
5. Move service: `sgraph_ai_service_playwright__cli/docker/service/Docker__Service.py` → `sg_compute_specs/docker/core/Docker__Service.py`. Refactor to use `sg_compute.platforms.ec2.helpers.*` instead of the legacy helpers.
6. Move user-data builder: → `sg_compute_specs/docker/user_data/Docker__User_Data__Builder.py`. Refactor to use `sg_compute.platforms.ec2.user_data.Section__*` composables.
7. Move CLI: `sgraph_ai_service_playwright__cli/docker/cli/` → `sg_compute_specs/docker/cli/`. Register with `sg-compute spec docker create / list / info / delete`.
8. Move routes: `sgraph_ai_service_playwright__cli/fast_api/routes/Routes__Docker__*.py` → `sg_compute_specs/docker/api/Routes__Spec__Docker.py`. Mount under `/api/specs/docker/...` in the new `Fast_API__Compute`.
9. Move tests: `tests/unit/sgraph_ai_service_playwright__cli/docker/` → `sg_compute_specs/docker/tests/`. Re-target imports.
10. **Compatibility shim** — leave a thin re-export at the legacy path that imports from the new location and prints a deprecation warning. This keeps `sp-cli` working until phase 4.
11. Update `team/roles/librarian/reality/sg-compute/index.md` with the docker spec entry.

**Acceptance criteria for phase 3.0:**

- `sg_compute_specs/docker/` is a real Python package with `manifest.py` exposing `MANIFEST: Schema__Spec__Manifest__Entry`.
- `Spec__Loader.load_all()` discovers it and includes it in the catalogue.
- All previously-passing docker tests still pass at the new location.
- Legacy `sp-cli docker create` still works via the shim (for now).
- `sg-compute spec docker create --instance-size small` works via the new CLI dispatcher (phase 4).

**Phase 3.1, 3.2, ... — one per remaining legacy spec.** Each is a standalone PR using the docker pattern. Sequence (ordered by complexity):

| Order | Spec | Notes |
|-------|------|-------|
| 3.0 | `docker` | simplest, no UI sub-panels |
| 3.1 | `linux` | promote from CLI; becomes a base for fractal composition |
| 3.2 | `podman` | nearly identical to docker |
| 3.3 | `vnc` | introduces the iframe/remote-browser pattern |
| 3.4 | `neko` | similar to vnc |
| 3.5 | `prometheus` | introduces metrics scraping |
| 3.6 | `opensearch` | data spec |
| 3.7 | `elastic` | data spec, introduces "import dashboards" workflow |
| 3.8 | `firefox` | most complex — has MITM sidecar, vault-write configuration column. **Requires the post-fractal-UI brief items 3 + 4 to land first** if those haven't. |

---

## Phase 4 — Control plane FastAPI

**Goal:** `Fast_API__Compute` exists and exposes the full `/api/{nodes,pods,specs,stacks}` surface. The dashboard can flip its base URL to point at it.

**Tasks:**

1. Create `sg_compute/control_plane/Fast_API__Compute.py` — `Serverless__Fast_API` shell with `setup_routes()` mounting:
   - `Routes__Compute__Nodes` (mounted at `/api/nodes`)
   - `Routes__Compute__Pods` (mounted at `/api/nodes/{node_id}/pods`)
   - `Routes__Compute__Specs` (mounted at `/api/specs`)
   - `Routes__Compute__Stacks` (mounted at `/api/stacks` — placeholder routes)
   - `Routes__Compute__Health` (`/api/health/info`, `/api/health/ready`)
   - All discovered per-spec route classes (mounted at `/api/specs/{spec_id}/...`)
2. Create the four `Routes__Compute__*` classes — pure delegation to `Node__Manager`, `Pod__Manager`, `Spec__Registry`, `Stack__Manager`.
3. Create `sg_compute/control_plane/lambda_handler.py` with Mangum wrapper for Lambda packaging parity.
4. Wire the `Fast_API__SP__CLI` legacy app to **also mount under `/legacy/`** alongside `/api/` — both app shells live in one process during the transition. Backwards-compat for any consumer still on `sp-cli` URLs.
5. Add an integration test: spin up `Fast_API__Compute` in-process, hit every route, assert shapes.

**Acceptance criteria:**

- `GET /api/specs` returns the catalogue with at least 2 entries (the migrated specs from phase 2 + phase 3.0).
- `POST /api/nodes` with `{ spec: "docker", ... }` creates a real EC2 instance (or a stubbed one in CI).
- `GET /api/nodes/{node_id}` returns the node's state.
- `DELETE /api/nodes/{node_id}` terminates.
- The legacy `sp-cli` URLs still respond from `/legacy/...`.

**Ship as one PR. Tag `phase-4__control-plane`.**

---

## Phase 5 — `sg-compute` CLI command

**Goal:** A single Typer entry-point `sg-compute` exists with the four verbs (`node`, `pod`, `spec`, `stack`) and dispatches to per-spec sub-commands discovered from the catalogue.

**Tasks:**

1. Create `sg_compute/cli/main.py` with the four top-level verbs.
2. `node_commands.py` exposes `sg-compute node {create, list, info, delete, logs}`. Spec-specific create takes `--spec <id>` plus per-spec fields.
3. `spec_commands.py` exposes `sg-compute spec {list, info, validate}` plus dispatches `sg-compute spec <id> <verb>` to the spec's own CLI module.
4. `pod_commands.py` exposes `sg-compute pod {list, start, stop, logs}` against a node-id.
5. `stack_commands.py` exposes placeholder stub for multi-node combinations.
6. Register the entry point in pyproject (`[project.scripts] sg-compute = "sg_compute.cli.main:app"`) — without flipping the package name yet (the entry script is `sg-compute`, the package name stays during phases 1-7).
7. Per-spec CLI modules (already moved during phase 3.x) get registered with the dispatcher via the manifest.

**Acceptance criteria:**

- `sg-compute --help` lists `node`, `pod`, `spec`, `stack`.
- `sg-compute spec list` shows every spec in the catalogue.
- `sg-compute spec docker create --instance-size small` creates a docker node end-to-end.
- The legacy `sp-cli` command is **not removed** in this phase; it lives alongside `sg-compute`.

**Ship as one PR. Tag `phase-5__cli`.**

---

## Phase 6 — Move host plane; rename `Routes__Host__Containers` → `Routes__Host__Pods`

**Goal:** The host control plane (the FastAPI that runs INSIDE each node) moves to `sg_compute/host_plane/`. The "container" vocabulary becomes "pod" everywhere in this tree.

**Tasks:**

1. `git mv sgraph_ai_service_playwright__host/ sg_compute/host_plane/`.
2. Inside, rename `containers/` → `pods/`. Update imports.
3. Rename `Routes__Host__Containers` → `Routes__Host__Pods`. Path: `/containers/list` → `/pods/list`, etc.
4. Rename `Container__Runtime` → `Pod__Runtime`, `Container__Runtime__Docker` → `Pod__Runtime__Docker`, etc.
5. Rename `Schema__Container__*` → `Schema__Pod__*`. Update field names where they say "container" (e.g. `container_count` → `pod_count` in `Schema__Host__Status`).
6. Update `docker/host-control/Dockerfile` entrypoint: `uvicorn sg_compute.host_plane.lambda_handler:_app ...`.
7. Update EC2 user-data templates that reference the host image to use the new entry point.
8. Update tests under `sg_compute__tests/host_plane/`.
9. Update the reality doc: `team/roles/librarian/reality/host-control/index.md` — rename file or content to reflect the move into `sg_compute/host_plane/`. Possibly rename the domain to `host_plane/` (Librarian call).

**Acceptance criteria:**

- Inside-the-node FastAPI starts with the new entry point.
- `GET /pods/list` returns what `GET /containers/list` returned.
- All 31 host_plane test functions pass at the new location.
- The control plane (phase 4) calls the new `/pods/...` paths when querying nodes.

**Ship as one PR. Tag `phase-6__host-plane-pods`.**

---

## Phase 7 — Fold `agent_mitmproxy` into `sg_compute_specs/mitmproxy/` AND fold the original Playwright service into `sg_compute_specs/playwright/`

**Goal:** The two top-level legacy packages (`sgraph_ai_service_playwright/` and `agent_mitmproxy/`) become specs in the catalogue.

This is two parallel sub-phases (7.A for mitmproxy, 7.B for playwright). They don't depend on each other; do them in either order or in parallel.

**Phase 7.A — `agent_mitmproxy/` → `sg_compute_specs/mitmproxy/`:**

1. `git mv agent_mitmproxy/fast_api/ sg_compute_specs/mitmproxy/api/`.
2. `git mv agent_mitmproxy/addons/ sg_compute_specs/mitmproxy/core/addons/`.
3. Create `sg_compute_specs/mitmproxy/manifest.py` declaring spec_id `mitmproxy`, capability `mitm-proxy`.
4. Move the Dockerfile + CI workflow into `sg_compute_specs/mitmproxy/dockerfile/`.
5. Update imports across the moved tree.
6. Tests: `tests/unit/agent_mitmproxy/` → `sg_compute_specs/mitmproxy/tests/`.

**Phase 7.B — `sgraph_ai_service_playwright/` → `sg_compute_specs/playwright/`:**

1. `git mv sgraph_ai_service_playwright/ sg_compute_specs/playwright/core/`.
2. Create `sg_compute_specs/playwright/manifest.py` declaring spec_id `playwright`, capability `browser-automation`.
3. The Lambda packaging stays — `sg_compute_specs/playwright/core/lambda_entry.py` is the entry point as before; pyproject is updated to reflect the new path.
4. Per-plugin UI components (none for playwright today) — N/A.
5. Tests retained in place under the new path.

**Acceptance criteria:**

- `Spec__Loader.load_all()` discovers `mitmproxy` and `playwright` and adds them to the catalogue.
- Lambda deployment of the playwright service still works (`pip install -e .` and `lambda_entry.handler` resolves).
- The mitmproxy admin FastAPI still responds on its port from the new location.

**Ship as two PRs. Tags `phase-7a__mitmproxy-fold` and `phase-7b__playwright-fold`.**

---

## Phase 8 — PyPI publish setup

**Goal:** `pyproject.toml` is rewritten to define **two** distributions: `sg-compute` (from `sg_compute/`) and `sg-compute-specs` (from `sg_compute_specs/`). A first release candidate is built and smoke-tested with `pip install`.

**Tasks:**

1. Decide on workspace layout — recommend two `pyproject.toml` files:
   - Root `pyproject.toml` for `sg-compute` (sources from `sg_compute/`).
   - `sg_compute_specs/pyproject.toml` for `sg-compute-specs` (sources from `sg_compute_specs/`).
2. Configure each pyproject:
   - `[project] name`, `version` (read from the package's own `version` file).
   - `dependencies` minimal — `osbot-utils`, `osbot-aws`, `osbot-fast-api`, `typer`, `fastapi` (sg-compute); `sg-compute>=X.Y` (sg-compute-specs).
   - `[project.scripts] sg-compute = "sg_compute.cli.main:app"` (only on sg-compute).
   - `[project.entry-points."sg_compute.specs"]` for any package wanting to expose specs (sg-compute-specs declares its own entry point per spec).
   - Tools config: pytest paths, mypy, ruff if used.
3. Configure wheel exclusions: `tests/`, `tests/**/*`, `__tests__/`, anything under `team/`, `library/`, etc.
4. Build both wheels: `python -m build` (or hatch / poetry per project convention).
5. Smoke-test in a fresh virtualenv: `pip install dist/sg_compute-*.whl dist/sg_compute_specs-*.whl`; run `sg-compute spec list` against a stub catalogue.
6. Decide on a TestPyPI publish for the first release candidate.

**Acceptance criteria:**

- `python -m build` produces wheels for both packages cleanly.
- `pip install sg-compute sg-compute-specs` in a fresh env succeeds.
- `sg-compute spec list` works against the installed catalogue.
- No tests are shipped in the wheels (verified by `unzip -l dist/*.whl | grep tests`).

**Ship as one PR. Tag `phase-8__pypi-build`.**

---

## Phase 9 — UI cosmetic rename `sp-cli-*` → `sg-compute-*`

**Goal (out of scope for backend team — listed for completeness):** the dashboard's web component prefix migrates. This is a frontend-only sweep; the backend plan does not own it. See [`20__frontend-plan.md`](20__frontend-plan.md) §9.

---

## Cross-cutting backend rules

These hold across every phase:

- **Type_Safe everywhere; no Pydantic; no Literals; no raw primitives.**
- **One class per file.** Empty `__init__.py`. Schemas, primitives, enums, collection subclasses each in their own file.
- **Routes have no logic.** Pure delegation to a service.
- **`osbot-aws` for AWS.** No direct boto3 calls anywhere new.
- **Tests: no mocks, no patches.** Use in-memory composition.
- **80-char `═══` headers** on every Python file (existing convention).
- **No docstrings.** Inline single-line comments only where the WHY is non-obvious.
- **Update the reality doc in the same commit as the code change.** Append a pointer to `team/roles/librarian/reality/changelog.md`.
- **Branch:** `claude/sg-compute-{phase}-{description}-{session-id}`.
- **PR title:** `phase-{N}: {short summary}`.
- **PR description:** link to this brief; list the acceptance criteria you checked.

---

## Open questions to flag with the Architect

- §8.1 of the architecture doc — **lock the closed `Enum__Spec__Capability` set** before phase 3.
- §8.2 — multi-platform routing strategy when `local` lands.
- §8.3 — confirm PEP 621 entry points as the spec discovery mechanism.
- Per-spec `pyproject.toml` (so each spec can publish independently in a later phase) — not in this brief; flag for the post-phase-9 follow-up.
