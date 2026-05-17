# sg-compute — Proposed

PROPOSED — does not exist yet. Items below extend the SG/Compute domain but are not in code today.

Last updated: 2026-05-17 | Domain: `sg-compute/`

---

## P-1 · `Section__Sidecar` user-data composable (BV2.2)

**What:** A user-data section that renders the ECR-login + `docker run` block for the host-control sidecar on every Node.

**Status note:** Listed as PROPOSED in the original 545-line index. Code at `platforms/ec2/user_data/Section__Sidecar.py` does exist (recorded in [`../platform.md`](../platform.md)). Keep this entry until the reality doc + brief are reconciled, since the BV2.2 wiring of all 10 spec `User_Data__Builder` classes still has loose ends per the history log.

## P-2 · Per-spec `Spec__Service__Base` common lifecycle base class

**What:** A shared base class that all per-spec `*__Service` classes (Docker, Ollama, Open_Design, …) extend, with default `health/exec/connect_target` implementations and a uniform `create_node` contract.

**Status note:** A `Spec__Service__Base` was introduced in v0.2.6 (see [`../specs.md`](../specs.md)). This proposed item tracks the broader rollout — i.e. migrating every spec service to the base class (today only `Ollama__Service` extends it).

## P-3 · `Node__Identity` — node-id generation/parsing helper

**What:** A small helper that owns node-id generation and parsing (today the logic is sprinkled across `Stack__Naming`, the per-spec mappers, and the EC2 helpers).

## P-4 · Remaining legacy specs migrated to `sg_compute_specs/` (phases 3.1–3.8)

**What:** Move the remaining legacy specs into the `sg_compute_specs/` tree following the same shape used for `docker` (B3.0): `linux`, `podman`, `vnc`, `neko`, `prometheus`, `opensearch`, `elastic`, `firefox`.

## P-5 · Vault-sourced sidecar API key

**What:** Follow-on to BV2.9 — wire the sidecar API key to be sourced from the vault rather than the current persistence stub.

## P-6 · Real vault I/O (v0.3 follow-on)

**What:** `Vault__Spec__Writer` currently uses an in-memory dict with `vault_attached=True`. Persistent vault wiring is deferred to v0.3.

---

## See also

- [`../index.md`](../index.md) — SG/Compute cover sheet
- [`../specs.md`](../specs.md) — vault writer and pilot specs
- [`../platform.md`](../platform.md) — `Section__Sidecar` (P-1)
- [`../cli.md`](../cli.md) — CLI surface (P-2 follow-on)
