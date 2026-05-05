# Debrief — phase-T2.1__BE: create_node for podman + vnc
**Date:** 2026-05-05
**Branch:** `claude/t2-be-1-MXKIP`
**Commit:** `02d57ea`
**Status:** COMPLETE

---

## What Was Done

Implemented T2.1 from brief `T2_1__create-node-podman-vnc.md`: `EC2__Platform.create_node` now handles docker, podman, and vnc via generic service dispatch (Option B).

### Changes

**Schema additions**
- `Schema__Podman__Create__Request`: added `registry: str = ''` and `api_key_ssm_path: str = ''`
- `Schema__Vnc__Stack__Create__Request`: added `registry: str = ''` and `api_key_ssm_path: str = ''`

**Service wiring**
- `Podman__Service.create_stack`: threads `registry` and `api_key_ssm_path` through to `Podman__User_Data__Builder.render()`
- `Vnc__Service.create_stack`: same for `Vnc__User_Data__Builder.render()`

**`create_node` on each spec service**
- `Docker__Service.create_node`: extracted from old `EC2__Platform._create_docker_node`; builds `Schema__Docker__Create__Request` then calls `create_stack` and returns `Schema__Node__Info`
- `Podman__Service.create_node`: same pattern for podman
- `Vnc__Service.create_node`: same pattern for vnc

**EC2__Platform refactor (Option B)**
- `_service_for(spec_id)`: new static method — returns wired service instance for docker/podman/vnc; raises `NotImplementedError` with spec_id in message for anything else
- `create_node`: generates SSM key + writes it, then delegates to `_service_for(spec_id).create_node(request, api_key_ssm_path=ssm_path)`
- `_create_docker_node`: removed; logic now lives in `Docker__Service.create_node`

---

## Test Coverage Added

| File | Tests |
|------|-------|
| `sg_compute__tests/stacks/podman/test_Podman__Service__create_node.py` | NEW — 7 tests: returns Schema__Node__Info, spec_id, state BOOTING, instance_id, ssm_path stored, ssm_path threaded to user_data, create_stack with new fields |
| `sg_compute__tests/stacks/vnc/test_Vnc__Service__create_node.py` | NEW — 7 tests: same contract for vnc |
| `sg_compute__tests/platforms/test_EC2__Platform.py` | Updated — 5 new tests: _service_for docker/podman/vnc returns correct type, unknown raises NotImplementedError, all 3 have create_node |

**Result:** 259 tests pass, 0 failures (control_plane tests excluded: `osbot_fast_api_serverless` not installed in local env; they pass in CI).

---

## Good Failures

1. **`Type_Safe` strict type enforcement on `ip_detector`**: Direct assignment of `_FakeIPDetector(Caller__IP__Detector)` failed because the annotation on `Podman__Service.ip_detector` is the spec-specific `sg_compute_specs.podman.service.Caller__IP__Detector`, not the platform-level one. Fix: subclass from the spec's own `Caller__IP__Detector` and use `object.__setattr__` for injection — matching the established test pattern.

2. **`Safe_Str__AMI__Id` / `Safe_Str__Instance__Id` strict regex**: `'ami-fake'` and `'i-podman-fake-001'` both rejected by `^ami-[0-9a-f]{17}$` / `^i-[0-9a-f]{17}$`. Fix: use 17-hex-char fake IDs (`ami-0a1b2c3d4e5f67891`, `i-0a1b2c3d4e5f67890`). Good failure — enforces realistic test data.

## Bad Failures

None.

---

## Follow-up Items

- T2.2 — Firefox CLI (`sg_compute_specs/firefox/cli/Cli__Firefox.py`)
- Remaining 9 specs still raise `NotImplementedError` from `_service_for`; this is the correct explicit failure mode per brief acceptance criteria
