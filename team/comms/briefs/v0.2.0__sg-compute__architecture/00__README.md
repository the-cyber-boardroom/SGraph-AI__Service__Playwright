# v0.2.0 — SG/Compute (architecture root)

**Status:** PROPOSED — to be ratified before BV2/FV2 phases start
**Codebase:** `the-cyber-boardroom/SGraph-AI__Service__Playwright` @ `v0.2.0` (just merged to main)
**Eventual:** `sgraph-ai/SG-Compute`

This folder contains the **shared architecture** that both Sonnet teams read. The per-team execution work lives in:

- [`team/comms/briefs/v0.2.0__sg-compute__backend/`](../v0.2.0__sg-compute__backend/) — backend phases BV2.x
- [`team/comms/briefs/v0.2.0__sg-compute__frontend/`](../v0.2.0__sg-compute__frontend/) — frontend phases FV2.x

Each phase is a **single self-contained brief file**. Read the relevant team folder's `00__README.md` for the phase index.

---

## Why v0.2

The v0.1.x migration delivered most of the structural work in two days but left:

- a few load-bearing gaps (`Pod__Manager`, generic node lifecycle, Lambda handler);
- five trees in dual-write state;
- an emergent **sidecar** sub-architecture that the original briefs never captured;
- security findings that need locking;
- the design decision (now ratified) that `linux` is dropped — every node is `AMI + docker + sidecar + spec-pods`.

**v0.2.0 is the merge to main.** v0.2.x is the patch series that closes the gaps and lands the security hardening + spec catalogue normalisation. v0.3 is the first cross-repo extraction milestone.

---

## Files in this folder

| File | Purpose |
|------|---------|
| [`00__README.md`](00__README.md) | This file — vision, decisions, where to read what |
| [`01__architecture.md`](01__architecture.md) | The taxonomy, two-package split, platforms, control plane, spec contract, legacy mapping |
| [`02__node-anatomy.md`](02__node-anatomy.md) | The Node baseline: AMI + Docker + sidecar + spec-pods. Why `linux` was dropped. |
| [`03__sidecar-contract.md`](03__sidecar-contract.md) | First-class sidecar architecture: ports, auth modes, CORS, API surface, sidecar-vs-control-plane partition |
| [`sources/`](sources/) | Code-review synthesis + pointers to the 6 audit/review reports from 2026-05-04 |

**Read order** for everyone: `00 → 01 → 02 → 03`. Then go to your team's folder.

---

## Decisions ratified in v0.2 (from the 2026-05-04 audit + handover)

1. **`linux` is permanently dropped.** Not a useful product offering on its own. See `02__node-anatomy.md`.
2. **Sidecar is first-class.** Documented as its own contract — see `03__sidecar-contract.md`. Port locked at `:19009`.
3. **`extends: []` is the convention.** All 12 specs use it. Composition mechanism is the user-data Section ordering, not the manifest's `extends` field. `Spec__Resolver` keeps the DAG check for future use.
4. **Two-package PyPI split locked.** `sg-compute` SDK + `sg-compute-specs` catalogue both ship from this repo.
5. **Per-spec `cli/` is OPTIONAL.** Specs without operator-facing verbs (e.g. `playwright`, `mitmproxy`) skip it.
6. **Cookie auth (Pattern C) for the WS shell.** Original brief proposed query-param or per-handler; team shipped cookie + iframe pattern. v0.2 hardens (`HttpOnly=true`, origin allowlist).
7. **Field renames in active use.** `stack_name → node_name`, `type_id → spec_id`, `container_count → pod_count`, `stack_id → node_id`. "Stack" reserved for multi-node combinations.
8. **Cross-repo extraction permitted for storage specs** before phase 8. `s3_server` shipped to its own repo as the precedent. Other specs stay here until v0.3+.
9. **Routes have NO logic.** Code review found `Routes__Compute__Nodes` violates this; backend phase BV2.4 cleans up.
10. **`Enum__Spec__Capability` is locked** as of 2026-05-04 with the 12 values currently in code.

---

## What v0.2.0 already ships (on main today)

- `sg_compute/` SDK with primitives, enums, schemas, `Platform`/`EC2__Platform`, `Spec__Loader`, `Spec__Resolver`, `Node__Manager`, `Fast_API__Compute` (real EC2 lifecycle wired)
- `sg_compute_specs/` catalogue with 12 specs (docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox, mitmproxy, playwright, ollama, open_design)
- Both pyproject.toml files; PyPI build setup; PEP 621 entry points
- `sg_compute/host_plane/` with the full sidecar (auth, CORS, `/docs-auth`, boot log, pod logs/stats, WS shell with cookie auth)
- Dashboard with `sp-cli-nodes-view` (6-tab node detail panel), F1 terminology label sweep complete

Known gaps to close in v0.2.x — see the team folders.

---

## Cross-cutting rules (apply everywhere)

- **Type_Safe everywhere.** No Pydantic, no Literals, no raw primitives, **no `: object = None` for DI** (code review finding).
- **One class per file.** Empty `__init__.py`.
- **Routes have no logic** — pure delegation to a service class.
- **`osbot-aws` for AWS** — no direct boto3.
- **Tests: no mocks, no patches.** `unittest.mock.patch` is forbidden in `sg_compute__tests/`.
- **No build toolchain** on the frontend. Native ES modules. Plain CSS.
- **80-char `═══` headers** on every Python file.
- **Branch:** `claude/{description}-{session-id}`. Never push to dev directly.
- **CLAUDE.md rule 9 (no underscore-prefix for private)** is **Python only**. JS files keep `_foo()` convention.

---

## Open questions (Architect-locked before specific phases)

| Question | Blocks | Recommended default |
|----------|--------|---------------------|
| Cookie `HttpOnly=true`? | BV2.19 | YES |
| CORS origin allowlist vs documented threat-model exception | BV2.19 | Allowlist |
| `__cli/aws/` → `sg_compute/aws/` or `sg_compute/platforms/ec2/aws/`? | BV2.8 | The latter |
| Vault-write contract first consumer | BV2.12 | Capability-agnostic — first to ship |
| UI assets from specs — endpoint vs StaticFiles | FV2.6 | Endpoint with caching |
