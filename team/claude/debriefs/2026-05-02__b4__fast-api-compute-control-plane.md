# B4 Debrief — Fast_API__Compute Control Plane

**Date:** 2026-05-02
**Branch:** `claude/sg-compute-b4-control-plane-xbI4j`
**Commit:** 77505a0
**Tests:** 27 new, 169 total (all green)

---

## What shipped

`sg_compute/control_plane/` — the FastAPI control plane for SG/Compute.

### New files (13)

| File | Purpose |
|------|---------|
| `control_plane/__init__.py` | Package marker |
| `control_plane/Fast_API__Compute.py` | FastAPI subclass; wires all routes |
| `control_plane/Spec__Routes__Loader.py` | Convention-based per-spec route discovery |
| `control_plane/routes/__init__.py` | Package marker |
| `control_plane/routes/Routes__Compute__Health.py` | `/api/health`, `/api/health/ready` |
| `control_plane/routes/Routes__Compute__Specs.py` | `/api/specs`, `/api/specs/{spec_id}` |
| `control_plane/routes/Routes__Compute__Nodes.py` | `/api/nodes` (placeholder) |
| `control_plane/routes/Routes__Compute__Stacks.py` | `/api/stacks` (placeholder) |
| `sg_compute__tests/control_plane/__init__.py` | Test package marker |
| `sg_compute__tests/control_plane/test_Fast_API__Compute.py` | 11 integration tests |
| `sg_compute__tests/control_plane/test_Routes__Compute__Health.py` | 4 health route tests |
| `sg_compute__tests/control_plane/test_Routes__Compute__Specs.py` | 5 spec catalogue tests |
| `sg_compute__tests/control_plane/test_Spec__Routes__Loader.py` | 7 loader tests |

### Route surface

```
GET  /api/health                          → {"status": "ok"}
GET  /api/health/ready                    → {"status": "ok", "specs_loaded": N}
GET  /api/specs                           → Schema__Spec__Catalogue (full list)
GET  /api/specs/{spec_id}                 → Schema__Spec__Manifest__Entry
GET  /api/nodes                           → placeholder
GET  /api/stacks                          → placeholder
POST/GET/DELETE /api/specs/docker/stack*  → delegated to Routes__Docker__Stack
POST/GET/DELETE /api/specs/podman/stack*  → delegated to Routes__Podman__Stack
```

---

## Key design decisions

**Convention-based route discovery (`Spec__Routes__Loader`)**

For `spec_id='docker'`, the loader imports `sg_compute_specs.docker.api.routes.Routes__Docker__Stack` and mounts it at `/api/specs/docker`. Specs without a route module are silently skipped. The import target is the per-class file (not the package `__init__.py`), because `__init__.py` files are empty per project rules.

**`Fast_API__Compute._make_service`**

Each per-spec route class carries a `service` type annotation. `_make_service` reads `routes_cls.__annotations__['service']`, instantiates it, and calls `.setup()` if present. This gives each spec a live service instance without `Fast_API__Compute` knowing anything about spec internals.

**`/{spec_id}` wildcard does not shadow per-spec routes**

FastAPI resolves specific paths before wildcards. `/api/specs/docker/stacks` reaches `Routes__Docker__Stack.list_stacks`, not the `/{spec_id}` handler in `Routes__Compute__Specs`. Confirmed by test and route introspection.

---

## Failures encountered

### Good failures

**`Spec__Routes__Loader` importing the package, not the class file**

First version of `_find_routes_class` imported `sg_compute_specs.docker.api.routes` (the package) and called `getattr(module, 'Routes__Docker__Stack')`. Since `__init__.py` is empty, this returned `None`. Caught immediately; fixed by importing the per-class module path `sg_compute_specs.docker.api.routes.Routes__Docker__Stack`.

**Route path type is `Safe_Str__Fast_API__Route__Prefix`, not `str`**

`r.path` on FastAPI route objects returns a `Safe_Str__Fast_API__Route__Prefix` wrapper. Test assertions using `in routes` against a set of these objects failed because `'/api/specs/docker/stacks' in {Safe_Str__Fast_API__Route__Prefix(...)}` is False. Fixed by normalising with `str(r.path)` in assertions.

**Docker stacks route raises `NoCredentialsError` in CI**

`TestClient` re-raises server exceptions by default. Test `test_spec_id_wildcard_does_not_shadow_docker_stacks` used `raise_server_exceptions=False` to capture the 500 without the test itself crashing.

---

## What is NOT here yet

- **`/api/nodes`** — placeholder only; wiring to `Node__Manager` is B5+
- **`/api/stacks`** — placeholder only; cross-spec aggregation is B5+
- **`/api/pods`** — not yet added; host-plane rename (`containers` → `pods`) is B6
- **Per-spec service with real `setup()` in tests** — test suite uses the default `Docker__Service()` with `setup()` called, which hits AWS; only route-mount tests run without AWS

## Next steps

- **B5**: `sg-compute` CLI with `node / pod / spec / stack` verbs
- **B6**: host-plane rename (`containers` → `pods`)
