# Code Review — SG/Compute SDK + spec catalogue

**Date** 2026-05-04 (UTC hour 22) · **Repo version** v0.1.171 · **Branch** dev (clean)
**Scope** `sg_compute/` (SDK) · `sg_compute_specs/` (12 specs) · `sg_compute__tests/` (SDK tests)
**Reviewer** Claude (read-only). No code modified.

---

## 1. Summary

The shape of the catalogue is good and the manifest contract is genuinely typed. The Spec__Loader/Spec__Resolver pair works (DAG check is real, cycle detection is correct, entry-point fallback is in place), the Routes__Compute__Specs surface is clean, and Type_Safe is the dominant idiom. The spec catalogue is more uniform than expected — 9 of 12 specs follow a near-identical layout. Boto3 is consistently quarantined inside `*__Helper.py` files with the "EXCEPTION — narrow boto3 boundary" comment.

**Concerning** the host-plane CORS config is reflectively permissive (`allow_origin_regex=r".*"` + `allow_credentials=True`) and the auth cookie is set with `httponly=False` — those two together create a credential-theft / CSRF surface. The "no mocks, no patches" rule is broken by `unittest.mock.patch`+`MagicMock` in the SDK tests (hardest violator: `test_Routes__Compute__Nodes.py`). Service classes universally type their dependencies as `: object = None`, which silently bypasses Type_Safe. Many service-shaped specs have no `Routes__*__Stack` test and no `*__Service` test — only the small builders/mappers are covered. `Pod__Manager` and `Routes__Compute__Pods` are still missing on the control plane (the host plane has its own `Routes__Host__Pods`). `EC2__Platform.create_node` raises `NotImplementedError`.

---

## 2. Findings

### 2.1 Spec catalogue consistency (item 1)

| Spec | manifest | extends | soon | create_endpoint_path | api/ | service or core | tests | layout |
|------|----------|---------|------|----------------------|------|-----------------|-------|--------|
| docker | ✅ | `[]` | ✅ | ✅ | ✅ routes | ✅ service/ | 4 | canonical |
| podman | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 4 | canonical |
| vnc | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 5 | canonical |
| neko | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 4 | canonical |
| prometheus | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 4 | canonical |
| opensearch | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 4 | canonical |
| elastic | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 4 | canonical |
| firefox | ✅ | `[]` | ✅ | ✅ | ✅ | ✅ service/ | 5 | canonical |
| ollama | ✅ | `[]` | ✅ | ✅ | ❌ no api/ | ✅ service/ | 1 (in-spec) | **deviates** — has `cli/`, no `api/routes` |
| open_design | ✅ | `[]` | ✅ | ✅ | ❌ no api/ | ✅ service/ | 1 (in-spec) | **deviates** — same pattern as ollama |
| mitmproxy | ✅ | **missing** | **missing** | **missing** | ✅ | ✅ core/ (no service/) | 12 | **deviates** — uses `core/` instead of `service/`, manifest is shorter |
| playwright | ✅ | **missing** | **missing** | **missing** | ❌ (under `core/fast_api/routes`) | ✅ core/service/ | 1 (in-spec) | **deviates** heavily — entire legacy tree under `core/` |

**Key deltas:**
- `mitmproxy` and `playwright` manifests omit the new fields (`extends`, `soon`, `create_endpoint_path`). They are valid because the schema defaults them, but they will not surface in any UI nav that filters on `create_endpoint_path`.
- `ollama` and `open_design` register their stack endpoints as `Routes__Open_Design__Stack` etc., but `Spec__Routes__Loader._find_routes_class` looks for `sg_compute_specs.{spec_id}.api.routes.Routes__{Pascal}__Stack` — these specs have no `api/` folder, so they will silently fail discovery and hang off the registry only (verified by inspection of `Spec__Routes__Loader.py:31-39`). The `create_endpoint_path` they advertise (`/api/specs/ollama`, `/api/specs/open_design`) is therefore unreachable through the auto-loader.
- `playwright` has its routes under `core/fast_api/routes/Routes__Sequence.py` etc. — also not picked up by `Spec__Routes__Loader`.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| 3 specs (mitmproxy, playwright, ollama via path) won't auto-mount via Spec__Routes__Loader | 🔴 | `sg_compute/control_plane/Spec__Routes__Loader.py:31-43` | Either standardise spec layout to `<spec>/api/routes/Routes__<Pascal>__Stack.py` for ollama/open_design/playwright, OR make the loader search a configurable list of locations (e.g. also `core/fast_api/routes/Routes__*`). Today the catalogue advertises endpoints that the loader cannot find. |
| `mitmproxy` & `playwright` manifests omit `extends`, `soon`, `create_endpoint_path` | ⚠ | `sg_compute_specs/mitmproxy/manifest.py:18-29`, `sg_compute_specs/playwright/manifest.py:18-29` | Add the three fields explicitly (default values are fine) so the manifest contract is uniform. |
| Spec layout drift: `service/` vs `core/` | ⚠ | mitmproxy + playwright | Document the canonical layout in `sg_compute/brief/` and migrate or grandfather the two outliers. |

### 2.2 Type_Safe discipline (item 2)

Sampled six files across the surface:

| File | Verdict | Notes |
|------|---------|-------|
| `Routes__Compute__Specs.py` (route) | ⚠ minor | Routes return raw `dict` (via `.json()`). Convention says return Type_Safe; calling `.json()` in the route is acceptable but the function signature is `-> dict`, which silently weakens the typed surface. |
| `Ollama__Service.py` (service) | 🔴 | All five DI fields typed as `aws_client : object = None` etc. Same pattern in `Docker__Service.py:33-38`, `Elastic__Service.py:43-46`, `Firefox__AWS__Client.py:23`, `Docker__Health__Checker.py:16`. This is a stealth raw-primitive — Type_Safe stops protecting the field once the type is `object`. |
| `Schema__Spec__Manifest__Entry.py` (schema) | ⚠ | Uses raw `str / int / bool` for `spec_id, display_name, icon, version, boot_seconds_typical, soon, create_endpoint_path`. Should use `Safe_Str__Spec__Id`, `Safe_Int__*`, etc. The repo has `Safe_Str__Spec__Id` already (`sg_compute/primitives/Safe_Str__Spec__Id.py`) but the schema does not import it. |
| `Enum__Spec__Capability.py` (enum) | ✅ | Clean str-Enum, kebab-case values, no Literals. |
| `Safe_Str__Spec__Id.py` (primitive) | ✅ | Correct regex, max length, mode. Good. |
| `Docker__User_Data__Builder.py` (builder) | ✅ | Type_Safe class, only `str/int` arguments to `render()` (acceptable as method args), template strings as module constants. |

**Literals / Pydantic leaks:** none found beyond comments referencing pydantic's auto-generation behaviour (the routes deliberately accept `body: dict` then call `from_json` to dodge FastAPI/pydantic's nested-schema generator — this is a workaround, not a leak). No `from typing import Literal` in production code.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| `: object = None` DI fields across spec services | 🔴 | `sg_compute_specs/{docker,elastic,ollama,open_design,firefox,…}/service/*__Service.py` (e.g. `Ollama__Service.py:29-33`) | Replace with the actual class type (after circular-import refactor) or with a typed `Optional[X]`. Today these defeat Type_Safe completely. |
| `Schema__Spec__Manifest__Entry` uses raw primitives | ⚠ | `sg_compute/core/spec/schemas/Schema__Spec__Manifest__Entry.py:17-27` | Replace `spec_id: str` with `Safe_Str__Spec__Id`; tighten `version`, `icon`, `create_endpoint_path` likewise. |
| Routes annotated `-> dict` | ⚠ | `Routes__Compute__Specs.py:26-34`, `Routes__Compute__Nodes.py:31-52`, `Routes__Docker__Stack.py:30-53` | Annotate with the actual Type_Safe schema class; FastAPI will then build the OpenAPI doc from it. |

### 2.3 Spec contract — manifest (item 3)

`Schema__Spec__Manifest__Entry` is exposed as `MANIFEST` in every one of the 12 manifest.py files (verified). All twelve `extends` values are either `[]` or absent (defaulting to `[]`) — confirmed. No spec composes on another yet. The mechanism exists but is unexercised.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| All `extends=[]` — composition contract is dormant | ⚠ | every `manifest.py` | Add at least one composing spec (e.g. `firefox` extends `mitmproxy` since the manifest already advertises `MITM_PROXY` capability) so the resolver's DAG path is exercised in production, not only in unit tests. |

### 2.4 Routes hygiene (item 4)

Sampled four route classes:

| Routes class | Verdict | Notes |
|--------------|---------|-------|
| `Routes__Compute__Specs` | ✅ | Pure delegation to `Spec__Registry`. No logic. |
| `Routes__Docker__Stack` | ✅ | Pure delegation to `Docker__Service`. Clean. |
| `Routes__Compute__Nodes` | 🔴 | Has business logic in `list_nodes` — credential-error mapping (`'credential' in str(e).lower()`) lives in the route. Constructs a raw dict `{'nodes': [...], 'total': N}` instead of returning a `Schema__Node__List`. Calls module-level `_platform()` (underscore-prefix violation) which hard-instantiates EC2__Platform — untestable without mocking the helper. |
| `Routes__Host__Auth` | ⚠ | Embeds a 130-line HTML template in the .py file and uses raw `@router.get` / `@router.post` decorators rather than `setup_routes` + `add_route_get`. Inconsistent with the rest of the route surface. |

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| Business logic + raw-dict return in Compute__Nodes | 🔴 | `sg_compute/control_plane/routes/Routes__Compute__Nodes.py:31-52` | Move credential mapping to a service. Add a `total` field to `Schema__Node__List` and return `listing.json()`. Replace `_platform()` helper with constructor injection (Type_Safe attr). |
| Auth-form HTML belongs outside the route file | ⚠ | `Routes__Host__Auth.py:26-140` | Move to a `host_plane/fast_api/templates/auth_form.html` and read from disk. |

### 2.5 Test coverage shape (item 5)

| Spec | spec-tree tests | sg_compute__tests/stacks | Targets covered | Gap |
|------|----------------|--------------------------|-----------------|-----|
| docker | 4 | 0 | manifest, tags-builder, user-data, mapper | **no Routes test, no Service test** |
| podman | 4 | 0 | (same shape) | **no Routes/Service test** |
| vnc | 5 | 0 | (same shape) | **no Routes/Service test** |
| neko | 4 | 0 | (same shape) | **no Routes/Service test** |
| prometheus | 4 | 0 | (same shape) | **no Routes/Service test** |
| opensearch | 4 | 0 | (same shape) | **no Routes/Service test** |
| elastic | 4 | 0 | (same shape) | **no Routes/Service test** |
| firefox | 5 | 0 | (same shape) | **no Routes/Service test** |
| ollama | 1 (manifest) | 3 | manifest, service, mapper, user-data | thin |
| open_design | 1 (manifest) | 3 | (same as ollama) | thin |
| mitmproxy | 12 | 0 | broad | best-covered spec |
| playwright | 1 (`test_package`) | 0 | n/a | legacy tests live in repo-root `tests/` |

**Mock usage in tests:**
- `sg_compute__tests/control_plane/test_Routes__Compute__Nodes.py` — 8 uses of `patch`/`MagicMock` (rule violation).
- `sg_compute__tests/host_plane/pods/test_Pod__Runtime__Docker.py` — 17 uses, but explicitly carved out at the subprocess boundary with a comment ("subprocess stubbed; narrow exception").
- `sg_compute__tests/stacks/ollama/test_Ollama__Service.py` and `…/open_design/test_Open_Design__Service.py` — 2 patches between them.
- All the spec-tree `tests/` (docker/elastic/neko/podman/etc.) — **0** mocks. They test only the pure components (builders, mappers, manifest, tag-builder) — which is why coverage is thin.

No `register_compute__in_memory()`-style in-memory composition helper exists for the SDK at all (verified by grep). The only test wiring pattern is `Fast_API()` + `add_routes(...)` + `TestClient(...)`. That's fine for routes that are constructor-injected, but `Routes__Compute__Nodes` resorts to module-level helpers, which is why that file pulls in mocks.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| 8 specs have zero Routes / Service tests | 🔴 | `sg_compute_specs/{docker,podman,vnc,neko,prometheus,opensearch,elastic,firefox}/tests/` | Add a `test_Routes__<Pascal>__Stack.py` with a TestClient-driven smoke per spec, using a fake `Service` injected via Type_Safe attr. |
| `unittest.mock.patch` in `test_Routes__Compute__Nodes.py` | 🔴 | `sg_compute__tests/control_plane/test_Routes__Compute__Nodes.py:7-9, 37-50, …` | Refactor `Routes__Compute__Nodes` to accept a `platform: Platform` attr (Type_Safe DI), then drop all patches. |
| No `register_compute__in_memory()` helper | ⚠ | n/a | Add a composition helper under `sg_compute/control_plane/` that builds `Fast_API__Compute` with injected `Platform` + `Spec__Registry`, mirroring the playwright pattern. |
| Subprocess mocks in Pod__Runtime tests | ✅ minor | `sg_compute__tests/host_plane/pods/test_Pod__Runtime__Docker.py` | Documented exception. Acceptable. |

### 2.6 Spec__Loader and Spec__Resolver (item 6)

Both classes are well-shaped.

- **Spec__Loader** discovers via two channels: the `sg_compute_specs/` package walk (`*/manifest.py`) and PEP 621 entry points (`sg_compute.specs`). Both branches are typed and re-raise wrapped errors. The package walk uses `importlib.util.spec_from_file_location` so the module is loaded in isolation — good for incubation.
- **Spec__Resolver.validate** does two passes: (1) every parent in `extends` must exist; (2) DFS cycle detection. The cycle check is sound. `topological_order` is provided as a helper for future composition.
- **Empty `extends` behaviour** — verified to be a no-op: the inner loops simply don't iterate. Resolver is safe under today's all-empty graph.

Concerns:

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| Docstrings present (rule violation: "Inline comments only") | ⚠ | `Spec__Loader.py:38, 64`, `Spec__Resolver.py:46` | Convert to inline `#` comments. |
| Underscore-prefix private methods (`_discover`, `_load_from_package`, `_load_from_entry_points`, `_load_manifest_module`, `_detect_cycle`) | ⚠ | `Spec__Loader.py:31-86`, `Spec__Resolver.py:27-41` | Rule says "no underscore prefix for private methods". Rename. |
| `Spec__Registry._specs` accessed externally | ⚠ | `Spec__Loader.py:28` (`resolver.validate(registry._specs)`) | Add a `Spec__Registry.snapshot() -> Dict[...]` accessor; don't reach into the private dict. |
| Entry-point branch swallows all exceptions | ⚠ | `Spec__Loader.py:77` (`except Exception: pass`) | At least log; otherwise a broken third-party spec is invisible. |

### 2.7 EC2__Platform (item 7)

**Real, but partial.** `list_nodes`, `get_node`, `delete_node` route through `EC2__Instance__Helper` which uses real boto3 (declared as the documented exception). The state mapping covers all six AWS instance states. Tags are read from the EC2 raw response; the `sg:stack-name` and `sg:purpose` convention is used to find spec-owned nodes — that's clean and consistent with what the spec services tag at launch.

**`create_node` raises `NotImplementedError`** with the message "call the spec-specific service directly". This is intentional (each spec creates EC2 instances through its own AWS client which knows the user_data, AMI lookup, IAM profile, etc.) — but it means `Routes__Compute__Nodes` cannot offer a generic create endpoint, and the unified node-management story is incomplete. There is no test for `EC2__Platform` (file exists but length suggests pure-mock-free tests).

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| `EC2__Platform.create_node` is a stub | ⚠ | `sg_compute/platforms/ec2/EC2__Platform.py:82-85` | Either remove from the abstract `Platform` interface (move create to spec services exclusively) or implement a generic dispatch that picks the spec service by `request.spec_id`. |
| Boto3 calls happen lazily inside method bodies | ⚠ | `EC2__Platform.py:58, 65, 71` | Hoist the helper imports to module top so `Spec__Registry`-bound services don't re-import per call (perf only; correctness is fine). |

### 2.8 Sidecar / host plane auth (item 8)

This is the area with the most surface concern.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| **CORS reflective `.*` origin + `allow_credentials=True`** | 🔴 | `sg_compute/host_plane/fast_api/Fast_API__Host__Control.py:71-78` | Any web page on any origin can call the host API in the user's browser using their auth cookie (`SameSite=lax` permits top-level cross-site cookies on safe methods, and `lax` does NOT block POSTs that the user navigates to). Add an explicit origin allowlist (the SG dashboard origin only). |
| **Cookie set with `httponly=False`** | 🔴 | `Routes__Host__Auth.py:163-167` | The api-key value is readable from JavaScript, so any XSS on the auth form's origin (which the host serves) leaks the key. Comment claims this is needed for "WS handshake" but browsers send cookies on WS handshakes regardless of httponly. Set `httponly=True`. |
| `_AUTH_FREE_PATHS` includes `/auth/set-auth-cookie` (POST) | ⚠ | `Fast_API__Host__Control.py:32` | Bypass is unauthenticated. The endpoint sets whatever value the body contains, so an attacker who reaches the endpoint can plant a known cookie. Add CSRF protection (origin check or one-shot token) or require api-key auth before the cookie can be set. |
| `samesite='lax'` + `allow_credentials=True` + reflective origin | 🔴 | combined | Lax is insufficient when the API permits non-GET cross-site state-changing calls and the cookie is the auth credential. Use `SameSite=Strict` for the cookie and tighten CORS to the dashboard origin. |
| `SHELL_COMMAND_ALLOWLIST` + `subprocess.run(..., shell=True)` | ✅ | `Shell__Executor.py:30-37`, `shell_command_allowlist.py`, `Safe_Str__Shell__Command.py` | Defence-in-depth is sound: regex strips `;|&$` etc., and the allowlist `startswith` check runs at primitive construction. Acceptable. |
| `Fast_API__Host__Control.setup` reads `version` from disk inside `setup()` | ⚠ | `Fast_API__Host__Control.py:40-42` | Path traversal `parent.parent.parent.parent` is brittle. Use `pathlib.Path(__file__).parents[3]`. Minor. |

### 2.9 Capability enum lock status (item 9)

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| Header still says "Architect locks set before phase 3" | ⚠ | `sg_compute/primitives/enums/Enum__Spec__Capability.py:4` | Either replace with "LOCKED on YYYY-MM-DD by Architect" plus the corresponding decision-log entry, or note the open status in the reality doc. The 12 enum values are used across all 12 manifests, so de-facto they're locked — the comment is just stale. |

### 2.10 Pod__Manager / Routes__Compute__Pods (item 10)

**Confirmed missing.**

- No file matches `Pod__Manager*` anywhere in `sg_compute/`, `sg_compute_specs/`, or `sg_compute__tests/` (grep returned 0 hits).
- `sg_compute/control_plane/routes/` contains `Routes__Compute__Health`, `Routes__Compute__Nodes`, `Routes__Compute__Specs`, `Routes__Compute__Stacks` only. **No `Routes__Compute__Pods`.**
- The host plane has its own `Routes__Host__Pods` and a `Pod__Runtime` / `Pod__Runtime__Docker` / `Pod__Runtime__Podman` / `Pod__Runtime__Factory` quartet under `sg_compute/host_plane/pods/service/`. Those run on the EC2 instance, not on the control plane.
- `sg_compute/core/pod/schemas/` exists with `Schema__Pod__Info` and `Schema__Pod__List` — the schemas are ready, the manager is not.

| Item | Severity | File:line | Recommendation |
|------|----------|-----------|----------------|
| `Pod__Manager` class missing | 🔴 | n/a | Implement under `sg_compute/core/pod/Pod__Manager.py` — the schemas already exist. Audit was correct. |
| `Routes__Compute__Pods` missing | 🔴 | n/a | Add to `sg_compute/control_plane/routes/`, mirroring `Routes__Compute__Nodes`. The control plane currently has no way to enumerate pods across all nodes — every consumer has to hop through individual host plane URLs. |

---

## 3. Out-of-scope additions the team built (good things)

1. **PEP 621 entry-point discovery** (`Spec__Loader._load_from_entry_points`) — third-party specs can register without being in the in-tree `sg_compute_specs/` package. Forward-looking and clean.
2. **`Spec__Resolver.topological_order`** — beyond the brief; ready for when composition lights up.
3. **Subprocess-bounded mocking convention** in `Pod__Runtime__Docker` tests — narrow exception, well-commented, doesn't pollute the rest of the test suite.
4. **`Caller__IP__Detector` + `Stack__Name__Generator`** as shared `sg_compute/platforms/ec2/networking/` helpers, reused by every spec service. Avoids duplication.
5. **`Docker__User_Data__Builder` `PLACEHOLDERS` tuple** — locked-by-test list of template variables. A nice contract-test hook.
6. **The `aws_name_for_stack` / `sg_name_for_stack` discipline** is already in service code — the AWS-naming guidance from CLAUDE.md is being followed.
7. **Mitmproxy spec has 12 tests** — the most thoroughly tested spec by a wide margin. Use as reference shape for the others.
8. **`shell_command_allowlist.py` shared between primitive validation and runtime check** — defence in depth done right.

---

## 4. Top 5 things to tackle in v0.2.x

1. **Lock the host-plane CORS / cookie story.** Replace `allow_origin_regex=r".*"` with an explicit dashboard-origin allowlist; flip the auth cookie to `httponly=True` + `SameSite=Strict`; gate `/auth/set-auth-cookie` behind the api-key middleware (UX cost is one extra header on the form's first submit). Without this, the sidecar API is reachable from any malicious page in the user's browser.
2. **Kill the `: object = None` DI pattern across spec services.** Replace with proper Type_Safe types or `Optional[X]` after resolving the circular-import excuse. This is the single biggest gap between the rule book and the reality of the spec tree.
3. **Build `Pod__Manager` + `Routes__Compute__Pods` on the control plane.** The schemas exist; the orchestration story doesn't. While at it, have `Routes__Compute__Nodes` accept a `platform` attr via Type_Safe DI so the test suite can drop `unittest.mock.patch`.
4. **Standardise spec layout.** Migrate `ollama`, `open_design`, `playwright`, `mitmproxy` to `<spec>/api/routes/Routes__<Pascal>__Stack.py`, OR teach `Spec__Routes__Loader` to look in `core/fast_api/routes/` as a fallback. Today three specs declare a `create_endpoint_path` that the loader cannot find. Add the missing manifest fields (`extends`, `soon`, `create_endpoint_path`) to mitmproxy and playwright manifests.
5. **Bring spec coverage to par.** Each of docker/podman/vnc/neko/prometheus/opensearch/elastic/firefox needs a TestClient-driven `test_Routes__<Pascal>__Stack.py` and a `test_<Pascal>__Service.py` — with a fake AWS client injected via Type_Safe DI, no `patch`. Promote the mitmproxy test layout to a template under `library/guides/`.

---

## 5. 🔴 Risks (consolidated)

| # | Risk | Where |
|---|------|-------|
| R1 | CORS reflective origin + credentials = cross-site auth use | `Fast_API__Host__Control.py:71-78` |
| R2 | `httponly=False` on api-key cookie = XSS exfil | `Routes__Host__Auth.py:163` |
| R3 | `SameSite=lax` cookie + reflective CORS = CSRF on state-changing calls | combined |
| R4 | `: object = None` DI defeats Type_Safe in every spec service | spec/service files, repeated |
| R5 | 8 of 12 specs lack Routes/Service tests | spec test trees |
| R6 | `unittest.mock.patch` violates no-mocks rule | `test_Routes__Compute__Nodes.py` |
| R7 | `Spec__Routes__Loader` silently misses 3 specs (ollama, open_design, playwright) | `Spec__Routes__Loader.py:31-39` |
| R8 | `Pod__Manager` and `Routes__Compute__Pods` missing | `sg_compute/core/pod/`, `sg_compute/control_plane/routes/` |
| R9 | `Routes__Compute__Nodes` has business logic + raw-dict return | `Routes__Compute__Nodes.py:31-52` |
