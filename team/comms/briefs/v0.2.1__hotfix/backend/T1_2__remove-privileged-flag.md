# T1.2 — Remove `--privileged` from `Section__Sidecar`

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.1, T1.3-T1.6).

## What's wrong

`sg_compute/platforms/ec2/user_data/Section__Sidecar.py` adds `--privileged` to the `docker run` command for the host-control container. **The brief did NOT ask for this.**

Combined with the `--volume /var/run/docker.sock:/var/run/docker.sock` mount (which IS in the brief), the sidecar gets kernel-level access to the host. A captured sidecar container = full host takeover (escape to host kernel, read other pods' memory, modify the EC2 boot environment, etc.).

## Why it matters

The Docker socket alone is enough to launch peer containers (sufficient for the brief's pod-CRUD requirement). `--privileged` adds host-kernel capabilities (CAP_SYS_ADMIN, raw network access, device access) that the sidecar does not need.

## Tasks

1. **Find the docker run** — `sg_compute/platforms/ec2/user_data/Section__Sidecar.py:NN` — locate the `--privileged` flag.
2. **Remove it.** Keep the `-v /var/run/docker.sock:/var/run/docker.sock` mount.
3. **Test the sidecar still works** — boot a Node; verify `GET /pods/list`, `POST /pods` (start a container), `DELETE /pods/{name}` all succeed via the sidecar.
4. **Test that escape is no longer possible** — try a known privileged-container escape (e.g. `nsenter -t 1 -m bash` to enter PID 1's mount namespace) inside the sidecar; expect EPERM.
5. **Document the security boundary** in `Section__Sidecar.py` header — single-line comment: `# Docker socket mount only — NEVER --privileged. Host-kernel access is not in the contract.`

## Acceptance criteria

- `grep "privileged" sg_compute/platforms/ec2/user_data/Section__Sidecar.py` returns zero hits.
- Pod CRUD via the sidecar still works (manual smoke test against a real Node, or osbot-aws fakes).
- Header comment documents the security boundary.
- Reality doc updated.

## "Stop and surface" check

If you find a pod-CRUD operation that fails without `--privileged`: **STOP**. The brief specifies Docker-socket access only. If a real use-case needs more, surface to Architect — do not silently re-add the flag.

## Live smoke test

Boot a docker Node; `docker ps` from the sidecar (via `/shell/execute` or directly) → expect a container list. Try `mount` inside the sidecar → expect failure for system mounts (proves `--privileged` is gone).

## Source

Executive review T1.2; backend-early review §"Top 2 security issue".
