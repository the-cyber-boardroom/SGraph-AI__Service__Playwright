# BV2.5 — `EC2__Platform.create_node` + `POST /api/nodes` + `lambda_handler.py`

## Goal

Three small pieces that together complete the control-plane lifecycle and Lambda packaging parity:

- `EC2__Platform.create_node` currently raises `NotImplementedError`. Implement it.
- `Routes__Compute__Nodes` is missing `POST /api/nodes`. Add it.
- `sg_compute/control_plane/lambda_handler.py` does not exist. Create it.

## Tasks

### Task 1 — Implement `EC2__Platform.create_node`

The signature already exists; it raises `NotImplementedError`. Implementation:

1. Take `Schema__Node__Create__Request` with `spec_id`, `instance_size`, `region`, `caller_ip`, optional `node_name`.
2. Look up the spec's manifest via `Spec__Registry`.
3. Look up the spec's `Service` class (e.g. `Docker__Service`) via the spec's `service/` module.
4. Instantiate the service with the platform reference; call `service.create_node(...)` with platform-level defaults filled in (region, AMI, SG handling).
5. Return `Schema__Node__Info`.

This is the **generic create flow** that the dashboard's "Create Node" launch form will use. Per-spec routes (`POST /api/specs/<id>/stack`) continue to work and SHARE the same underlying implementation.

### Task 2 — Add `POST /api/nodes` to `Routes__Compute__Nodes`

After BV2.4 (route refactor) lands. Pure delegation: `def create_node(self, request: Schema__Node__Create__Request) -> dict: return self.platform.create_node(request).json()`.

### Task 3 — Build `sg_compute/control_plane/lambda_handler.py`

Mangum wrapper around `Fast_API__Compute`. Mirrors the `host_plane/fast_api/lambda_handler.py` pattern. The control plane should be Lambda-deployable.

## Acceptance criteria

- `EC2__Platform.create_node` returns a real `Schema__Node__Info` for at least 3 specs (docker, podman, vnc) — integration test against a stubbed boto3 if no AWS creds.
- `POST /api/nodes` works end-to-end.
- `lambda_handler.py` imports cleanly; `_app` resolves; Mangum is wired.
- All tests pass; no `unittest.mock.patch`.

## Open questions

- **Per-spec parameter passing.** Different specs need different create params (firefox needs MITM script handle, elastic needs cluster-name, etc.). Two options:
  - (a) `Schema__Node__Create__Request.spec_params: Schema__Spec__Params__Base | None` — typed open envelope.
  - (b) Per-spec routes stay the canonical create path; `POST /api/nodes` only handles the no-extras case.
  Recommend (a) with `spec_params` extending the base. Architect to ratify.

## Blocks / Blocked by

- **Blocks:** FV2.5 (frontend launch flow against `POST /api/nodes`).
- **Blocked by:** BV2.4 strongly recommended (you don't want to add a new endpoint to a route class that's about to be refactored).

## Notes

Per-spec create routes (`POST /api/specs/docker/stack`) continue to work. They become a thin wrapper around the generic create — they just pre-fill `spec_id` from the URL path. This duplication is acceptable for v0.2.x.
