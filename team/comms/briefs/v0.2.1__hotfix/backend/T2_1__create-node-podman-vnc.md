# T2.1 — `EC2__Platform.create_node` for podman + vnc (3 specs total)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

BV2.5 brief required `EC2__Platform.create_node` for **at least 3 specs** (docker, podman, vnc). Implementation works for **docker only**. Other 9 specs raise `NotImplementedError`. The PR description and debrief don't flag this — silent scope cut marked "done".

## Tasks

1. **Implement `_create_podman_node`** following the `_create_docker_node` pattern. Extract the common Section assembly into a helper if it reduces duplication.
2. **Implement `_create_vnc_node`** — note this spec has additional requirements (X server, noVNC), check `sg_compute_specs/vnc/service/Vnc__User_Data__Builder.py` for the spec-specific user-data sections.
3. **Decide on the dispatch pattern** for the remaining 9 specs:
   - Option A — implement them all now (per-spec branches in `EC2__Platform.create_node`).
   - Option B — generic dispatch via `Spec__Loader.get_spec(spec_id).service.create_node(...)` — service-level polymorphism instead of platform-level branches. Recommended; less code; lets specs own their create logic.
4. **If Option B**: the per-spec `<Pascal>__Service.create_node` becomes the canonical entry; `EC2__Platform.create_node` is a thin dispatcher.
5. **Tests** — for each of 3 specs, an integration test against `EC2__Platform.create_node` that asserts it produces a valid `Schema__Node__Info`. No mocks; use osbot-aws fakes if no AWS creds in CI.

## Acceptance criteria

- `EC2__Platform.create_node(Schema__Node__Create__Request__Base(spec_id='docker'))` works.
- Same for `'podman'` and `'vnc'`.
- The remaining 9 specs either work (Option B) or raise a clear `NotImplementedError("spec X create not yet wired in EC2__Platform")` — never silently fail.
- Debrief uses `PARTIAL` if any spec is left as TODO, with a follow-up brief filed.

## Live smoke test

Manually launch a docker, podman, and vnc Node via `POST /api/nodes` (with auth post-T1.1). Verify each appears in `GET /api/nodes` and is reachable via its sidecar.

## Source

Executive review Tier-2; backend-early review §"Top missed requirement #1".
