# Host Plane (Pointer)

**Domain:** `sg-compute/` | **Subarea:** `sg_compute/host_plane/` | **Last updated:** 2026-05-17

The host-control plane code lives **inside the SG/Compute package** at `sg_compute/host_plane/`, but the runtime HTTP surface it exposes is documented as a separate reality domain because it runs on a different host (the ephemeral EC2 sidecar at port `:19009`, not the SG/Compute control plane).

This file is a deliberate pointer rather than a duplicate.

---

## EXISTS

| What | Where |
|------|-------|
| Canonical package | `sg_compute/host_plane/` |
| Subpackages | `host_plane/containers/`, `host_plane/shell/`, `host_plane/host/`, `host_plane/pods/`, `host_plane/images/`, `host_plane/fast_api/` |
| Image build | `docker/host-control/` (built by `ci-pipeline.yml`) |
| Sidecar wiring | Installed on every Node by `Section__Sidecar` (BV2.2) — see [`platform.md`](platform.md) |
| Sidecar consumer | `Sidecar__Client` in `sg_compute/core/pod/` — see [`pods.md`](pods.md) |

**For the full HTTP surface, route classes, schemas, allowlist, image, and tests:**
see [`../host-control/index.md`](../host-control/index.md).

### BV2.1 note (2026-05-04)

`sgraph_ai_service_playwright__host/` was an orphaned copy of `sg_compute/host_plane/` and has been **deleted**. The authoritative package is `sg_compute/host_plane/` only. The CI workflow (`ci__host_control.yml`) no longer tests the orphan; the host image builds from `sg_compute/host_plane/` via `ci-pipeline.yml`. Sidecar port is **`:19009`** (not `:9000`).

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`../host-control/index.md`](../host-control/index.md) — full host-control HTTP surface, schemas, allowlist, tests
- [`platform.md`](platform.md) — `Section__Sidecar` (installs this image at boot)
- [`pods.md`](pods.md) — `Pod__Manager` + `Sidecar__Client` (consumes the host-control endpoints)
