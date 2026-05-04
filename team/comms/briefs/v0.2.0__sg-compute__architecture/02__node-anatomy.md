# 02 — Node Anatomy (`linux` is dropped)

The shortest brief in the v0.2 set, but the most important to internalise. **Read before touching any spec or any user-data builder.**

---

## What every Node is in v0.2

```
                    ┌─────────────────────────────────────┐
                    │   Node                              │
                    │   (one EC2 instance today)          │
                    │                                     │
                    │   ┌───────────────────────────────┐ │
                    │   │ AMI  (AL2023 base, or baked)  │ │
                    │   └───────────────────────────────┘ │
                    │                                     │
                    │   ┌───────────────────────────────┐ │
                    │   │ Docker  (or Podman runtime)   │ │
                    │   │ — installed by Section__Docker│ │
                    │   └───────────────────────────────┘ │
                    │                                     │
                    │   ┌───────────────────────────────┐ │
                    │   │ Sidecar — Fast_API__Host      │ │
                    │   │ — listens on :19009           │ │
                    │   │ — installed by Section__Sidecar│ │
                    │   └───────────────────────────────┘ │
                    │                                     │
                    │   ┌───────────────────────────────┐ │
                    │   │ Spec pods                     │ │
                    │   │ — what makes this Node a      │ │
                    │   │   "firefox node" or           │ │
                    │   │   "elastic node"              │ │
                    │   │ — installed by spec's         │ │
                    │   │   <Pascal>__User_Data__Builder│ │
                    │   └───────────────────────────────┘ │
                    └─────────────────────────────────────┘
```

The first three layers — AMI, Docker, sidecar — are the **Node baseline**. The fourth — spec pods — is what differentiates one Node type from another.

---

## Why `linux` was dropped (from B3.1)

The original v0.1.140 plan listed `linux` as the first spec to migrate, intended as the fractal-composition base (`firefox extends [linux, docker]` etc.). **The team dropped it on purpose.** Three reasons:

1. **It's not a useful product offering.** A "bare Linux node" is a node baseline with no application — there's nothing for the operator to do with it that they couldn't do via `sg-compute spec docker create` (which gets them a node with Docker + sidecar) and then running pods themselves.
2. **The composition story didn't survive contact.** The brief's intent was that every spec `extends=['linux']`. Reality: every spec already gets `linux + docker + sidecar` for free via the user-data composables (`Section__Base + Section__Docker + Section__Sidecar`). `extends` would just duplicate that.
3. **The sidecar emerged.** Once every Node started running the host-plane FastAPI, the "shell access" use-case that "bare Linux" was supposed to solve is now better served by the sidecar's `WS /shell/stream` (with allowlist + cookie auth) on any Node — including `docker`, `firefox`, `elastic`, etc.

So `linux` is gone. Forever. **Do not re-introduce it.** If a new spec needs to declare its dependencies, `extends=[]` is the correct and current convention.

---

## What the Node baseline gives every spec (for free)

The user-data builder for any spec assembles these Sections in order:

| Section | What it does |
|---------|--------------|
| `Section__Base` | hostname, locale, `dnf update`, `systemd` setup |
| `Section__Docker` | install Docker (or Podman) + start the daemon + ensure socket permissions |
| `Section__Sidecar` | **NEW in v0.2** — pull the host-control-plane image, run with API key in env, expose `:19009`, register `/auth/set-cookie-form`, etc. |
| `Section__Env__File` | write `/run/<spec>/env` to tmpfs with secrets |
| `Section__Shutdown` | `systemd-run` auto-terminate timer + `InstanceInitiatedShutdownBehavior=terminate` |
| `Section__<Spec>` | spec-specific bash — pull spec containers, configure nginx if needed, etc. |

**The order matters.** Sidecar must come AFTER Docker (it runs as a container) and BEFORE any spec containers (so the operator can use the sidecar to debug a stuck spec).

`Section__Sidecar` is **NEW for v0.2.0.** Prior to v0.2 the sidecar install was inlined into spec-specific user-data (or absent). The `Section__Sidecar` module factors out the boilerplate so every spec gets the sidecar identically. **BV2.1 builds this module.**

---

## What "every Node has a sidecar" means in practice

For the dev teams:

- **Frontend can always assume** that every Node exposes `:19009` once boot completes. `host_api_url = http://{public_ip}:19009` is derivable from `public_ip` alone (the handover doc's recommended fallback pattern is now the canonical one).
- **The spec's API surface is partitioned.** Operations that need IAM (e.g. `describe-instances`) belong on the SP CLI / control plane (which has IAM credentials). Operations that act on the Node itself (pods, shell, host metrics) belong on the sidecar. Code review found one violation already corrected (commit `1c96fbe`: ec2-info moved from sidecar to SP CLI catalog because the sidecar has no IAM). **BV2.7 documents this partition formally** — see [`03__sidecar-contract.md`](03__sidecar-contract.md) §"Sidecar vs control-plane boundary".
- **Health-check semantics.** A Node's `state` transitions from `BOOTING` → `READY` only after **the sidecar responds to `/health`**. Cloud-init complete is not enough; the sidecar's container must be up. Code review flagged a state-vocabulary mismatch (`'running'` hardcoded in 6 frontend sites vs `Schema__Node__Info` returning `'ready'` or `'READY'`). **FV2.1 fixes this on the frontend side; BV2.2 confirms canonical state values in `Enum__Node__State`.**

---

## What this changes for the spec authors

If you are migrating a legacy `__cli/<spec>/` spec into `sg_compute_specs/<spec>/` (BV2.4 territory):

1. **Drop any `extends: ['linux']`** — should be `extends: []`. Reality: code review confirmed all 12 specs already use `[]`.
2. **Replace inline sidecar install** in your `<Spec>__User_Data__Builder.py` with `Section__Sidecar` from `sg_compute/platforms/ec2/user_data/`. Until BV2.1 builds it, leave the inline install but mark it `# TODO(BV2.1): replace with Section__Sidecar`.
3. **Verify your Section__<Spec> doesn't conflict** with the sidecar's port (`:19009`) or paths.

If you are writing a NEW spec (post-v0.2.1):

1. Skip the inline sidecar install entirely — `Section__Sidecar` does it.
2. Your `Section__<Spec>` only needs to handle the application layer (pull your spec's container images, configure their entry points, expose ports).
3. The sidecar is already there when your section runs.

---

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-04 | `linux` is permanently dropped as a spec | Not a useful product offering on its own; the baseline + sidecar already provides shell access |
| 2026-05-04 | Every Node carries `Section__Sidecar` in user-data | Frontend / operators can assume `:19009` is always available once a Node is `READY` |
| 2026-05-04 | `extends: []` is the default and current convention | The composition mechanism is the user-data Section ordering, not the manifest's `extends` field |
| 2026-05-04 | Node `state` transitions to `READY` only after sidecar `/health` succeeds | Defines a single canonical readiness signal |

---

## Out of scope for this document

- The sidecar's API surface, auth, CORS — see [`03__sidecar-contract.md`](03__sidecar-contract.md).
- Multi-platform Node anatomy (K8s pod, GCP VM, local Docker) — defer to v0.3.
- Stack (multi-Node) anatomy — defer to v0.3.
