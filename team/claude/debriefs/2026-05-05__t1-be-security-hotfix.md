# Debrief — phase-T1__BE-security-hotfix
**Date:** 2026-05-05
**Branch:** `claude/t1-be-hotfix-MXKIP`
**Commit:** _(backfill after merge)_
**Status:** COMPLETE

---

## What Was Done

Implemented all 6 Tier-1 backend security fixes in one PR as instructed by `team/comms/briefs/v0.2.1__hotfix/backend/`.

### T1.1 — Fast_API__Compute must require API key
- Changed base class from `Fast_API` (enable_api_key=False) to `Serverless__Fast_API` (enable_api_key=True)
- **Critical follow-up discovered**: `Fast_API__Compute.setup()` overrode the parent without calling `super().setup()`, so `setup_middlewares()` was never called — the auth middleware was never registered even after the base-class change. Fixed by calling `self.setup_middlewares()` explicitly at the start of `setup()`.
- Added `_Middleware__Health_Bypass` inner class to pass `/api/health` and `/api/health/ready` through unauthenticated (load-balancer / Lambda probes).

### T1.2 — Remove `--privileged` from `Section__Sidecar` docker run
- Removed `--privileged` flag from the TEMPLATE in `Section__Sidecar.py`. Docker socket mount (`-v /var/run/docker.sock:/var/run/docker.sock`) is sufficient for sidecar operations.

### T1.3 — API key via SSM SecureString, not plaintext user-data
- Created `SSM__Sidecar__Key` in `sg_compute/platforms/ec2/secrets/` — deterministic SSM path `/sg-compute/nodes/{node_id}/sidecar-api-key`, backed by `osbot_aws.helpers.Parameter`.
- `Section__Sidecar.render()` now takes `api_key_ssm_path` (SSM path) instead of `api_key_value` (plaintext). At EC2 boot, user-data fetches the key via `aws ssm get-parameter --with-decryption`.
- Added `host_api_key_ssm_path` field to `Schema__Node__Info` — computed deterministically by `EC2__Platform._raw_to_node_info()` via `SSM__Sidecar__Key.path_for(node_id)`.
- `EC2__Platform._create_docker_node()` generates a `secrets.token_urlsafe(32)` key and writes it to SSM before launching the EC2 instance.

### T1.4 — POST /api/nodes now auth-gated
Fixed transitively by T1.1 (the middleware now actually runs) and T1.3 (no more empty-key bug path).

### T1.5 — Per-node key lookup in Pod__Manager
- `Pod__Manager._sidecar_client()` now calls `_resolve_api_key(node_id, ssm_path)` which reads the per-node SSM key first and falls back to the `SG_COMPUTE__SIDECAR__API_KEY` env var only for local-dev.
- Bulk-renamed `api_key_value` → `api_key_ssm_path` across all 14 spec User_Data__Builder files.

### T1.6 — Boot assertions in both control-plane services
- `Fast_API__Compute._assert_api_key_configured()`: raises `AssertionError` if `FAST_API__AUTH__API_KEY__VALUE` is unset or < 16 chars.
- `Fast_API__Host__Control._assert_api_key_configured()`: same pattern.

---

## Test Coverage Added / Updated

| File | Change |
|------|--------|
| `sg_compute__tests/control_plane/test_Fast_API__Compute__auth.py` | NEW — 12 negative-path auth tests (401 without key, 200 with key, health bypass, boot assertions) |
| `sg_compute__tests/platforms/ec2/secrets/test_SSM__Sidecar__Key.py` | NEW — path computation + class structure (no AWS calls) |
| `sg_compute__tests/platforms/ec2/user_data/test_Section__Sidecar.py` | Updated — `api_key_value` → `api_key_ssm_path`; added `test_render_fetches_key_from_ssm`, `test_render_has_no_privileged_flag` |
| `sg_compute__tests/platforms/test_EC2__Platform.py` | Updated — assert `host_api_key_ssm_path` in `_raw_to_node_info` result |
| `sg_compute__tests/control_plane/test_Fast_API__Compute.py` | Updated — env var setUp/tearDown; auth header on TestClient; wildcard test accepts 401 |
| `sg_compute__tests/control_plane/test_Legacy__Routes__Mount.py` | Updated — env var setUp/tearDown; `authed_client` + `anon_client` split |
| `sg_compute__tests/control_plane/test_Routes__Compute__Nodes.py` | Updated — `_client_with_handler()` sets env var and passes key header |
| `sg_compute__tests/control_plane/test_Spec__UI__Static__Files.py` | Updated — env var setUp/tearDown; `_authed_client()` helper |
| `sg_compute__tests/control_plane/test_lambda_handler.py` | Updated — `setUpModule`/`tearDownModule` + `sys.modules` eviction |
| `sg_compute__tests/host_plane/fast_api/test_Fast_API__Host__Control.py` | Updated — CORS tests fixed: `allow_credentials=True` reflects origin, not `*` |

**Result:** 384 tests pass, 0 failures.

---

## Good Failures

1. **`setup_middlewares()` was never called**: Caught by the new auth tests asserting 401. Without the tests, the T1.1 base-class change would have had zero effect in production — middleware was never registered. The tests exposed this immediately.

2. **CORS `access-control-allow-origin: '*'` assertion wrong**: Starlette reflects the actual Origin when `allow_credentials=True` — `'*'` + credentials is invalid CORS per spec. Two existing tests asserted `== '*'`. The re-run exposed the mis-assertion; we updated to assert the reflected origin.

## Bad Failures

None. All issues were caught and fixed in the same session.

---

## Follow-up Items

- T2.x work can now begin (see `team/comms/briefs/v0.2.1__hotfix/00__README.md` for ordering)
- IAM policy granting the EC2 instance role `ssm:GetParameter` on `/sg-compute/nodes/*` is a prerequisite for T1.3 to work in production (DevOps task; out of scope here)
- The `test_Routes__Compute__Pods.py` `Fake__Pod__Manager` bypasses `_sidecar_client` entirely, so it remains unaffected by T1.5
