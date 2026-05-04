# BV2.2 — Build `Section__Sidecar` user-data composable

## Goal

Every Node ships with the sidecar (`Fast_API__Host__Control` on `:19009`) per the v0.2 baseline (see `architecture/02__node-anatomy.md`). Today, the sidecar install is inlined into each spec's `<Pascal>__User_Data__Builder.py`. Factor it out into a reusable `Section__Sidecar` composable so:

- Adding a new spec doesn't require copy-pasting sidecar bash;
- A future change to the sidecar install (image tag, env vars, CMD args) lands in one place;
- The Section is unit-testable in isolation.

## Tasks

1. Create `sg_compute/platforms/ec2/user_data/Section__Sidecar.py`. Use `Section__Base.py` and `Section__Docker.py` as the model. The new section:
   - Pulls the `host-control` image from ECR (image tag is a parameter so callers can pin).
   - Runs the container detached on port `19009`, with `--restart unless-stopped`.
   - Injects API key via `FAST_API__AUTH__API_KEY__VALUE` env var (read from a tmpfs file written by `Section__Env__File`).
   - Sets `--name sg-sidecar` for predictable container management.
   - Mounts `/var/run/docker.sock` for pod CRUD access.
2. Add a Type_Safe schema for the section's parameters: `Schema__Section__Sidecar__Params` with fields `image_tag : Safe_Str__Image__Tag`, `port : Safe_Int__Port` (default 19009), `api_key_env_var : Safe_Str__Env__Var__Name`.
3. Refactor each spec's `<Pascal>__User_Data__Builder.py` to call `Section__Sidecar` instead of the inline install. Touch all 12 specs but keep the change mechanical — no behaviour changes beyond the refactor.
4. Add unit tests for `Section__Sidecar` — verify the rendered bash script contains the expected `docker pull`, `docker run`, env injection, port mapping. **No mocks.**
5. Update `architecture/02__node-anatomy.md` § "What the Node baseline gives every spec" — `Section__Sidecar` is now real. (Append a "STATUS: implemented in BV2.2 (commit X)" line.)

## Acceptance criteria

- `sg_compute/platforms/ec2/user_data/Section__Sidecar.py` exists and is unit-tested.
- All 12 specs' `<Pascal>__User_Data__Builder.py` use `Section__Sidecar`. Inline `docker run host-control` bash is removed.
- The rendered user-data for any spec still produces a working Node (smoke test against EC2 if AWS creds available; otherwise integration test of the bash assembly).
- Reality doc updated.

## Open questions

- **Sidecar image tag pinning policy.** Should every spec pin to a specific tag (`:0.2.0`) or float on `:latest`? Recommend **pin** — eliminates surprise upgrades. Architect to ratify before this phase.

## Blocks / Blocked by

- **Blocks:** nothing strict, but BV2.13 (spec layout normalisation) will be cleaner if this lands first.
- **Blocked by:** BV2.1 (orphan delete) — not strict, but reduces confusion about which `host-control` is the real one.

## Notes

The image is published from `docker/host-control/Dockerfile`. Tag conventions follow the repo's existing image tagging (the CI pipeline auto-tags from `sg_compute/version`). The Section parameter takes the tag as a string; the spec's User_Data__Builder picks the right tag for its target environment (default: pin to the sg_compute version that built the spec).
