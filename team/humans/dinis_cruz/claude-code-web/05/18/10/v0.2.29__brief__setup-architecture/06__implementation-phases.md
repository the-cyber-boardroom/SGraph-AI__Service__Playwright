---
title: "06 — Implementation phases"
file: 06__implementation-phases.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 06 — Implementation phases

## Phase A — Unblock today's bootstrap (SMALL, ~half a day)

**Goal:** the operator can re-run `sg vault-publish bootstrap` without
the `ResourceConflictException` blowing up. Pure idempotency bandage,
no new architecture.

**Scope:**
- `Lambda__AWS__Client.ensure_function_url(name)` — checks then creates
- `CloudFront__AWS__Client.ensure_distribution(req)` — find-by-alias,
  then create or return existing
- `Vault_Publish__Service.bootstrap` switches to `ensure_*`
- Same tests as today, plus "re-run is no-op" test cases

**Acceptance:**
```
sg vault-publish bootstrap        # creates everything; → bootstrapped
sg vault-publish bootstrap        # second run; → 'already bootstrapped'; exit 0
```

**Owner:** Dev. Size: half a day.

---

## Phase B1 — Setup skeleton + IAM area (MEDIUM)

**Goal:** the `setup/` sub-package exists, the IAM area is fully
implemented (create/update/delete/check/status), and the CLI surface
works. IAM first because it has the cleanest drift story (we have
`Waker__Policy__Template`).

**Scope:**
- `sg_compute_specs/vault_publish/setup/` folder + manifest
- `Enum__Setup__State`, `Schema__Setup__Issue`,
  `Schema__Setup__Action` primitives
- `Setup__IAM` with all five verbs
- `Schema__Setup__IAM__Report`
- `Cli__Setup` mounted at `sg vault-publish setup`
- `sg vault-publish setup iam {check,status,create,update,delete}`
- In-memory IAM client for tests, full coverage of drift cases
- Gates: `SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1` for
  create/update, `*_ALLOW_DELETES=1` for delete

**Acceptance:**
```
sg vault-publish setup iam check                    # OK or DRIFT report
sg vault-publish setup iam check --diff             # shows policy diff
SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 \
  sg vault-publish setup iam update                 # applies policy
```

**Owner:** Dev. Size: ~1.5 days.

---

## Phase B2 — Lambda + Function URL areas (MEDIUM)

**Goal:** `setup lambda` and `setup url` are implemented. Drops the
need for Phase A's `ensure_function_url` bandage (Phase A code can be
removed at end of B2).

**Scope:**
- `Setup__Lambda` with all five verbs
- `Setup__Function_URL` with all five verbs
- `Schema__Setup__Lambda__Report`,
  `Schema__Setup__Function_URL__Report`
- CLI: `sg vault-publish setup lambda ...`,
  `sg vault-publish setup url ...`
- Lambda's `check` does the SHA256 comparison to detect "code changed
  but not deployed" drift
- Tests with in-memory Lambda client

**Acceptance:**
```
sg vault-publish setup lambda check       # OK; or DRIFT: code changed
sg vault-publish setup lambda update      # re-deploys
sg vault-publish setup url check          # OK or MISSING
sg vault-publish setup url create         # idempotent
```

**Owner:** Dev. Size: ~2 days.

---

## Phase B3 — CloudFront + ACM + DNS areas (MEDIUM)

**Goal:** the remaining setup areas. ACM is check-only, CF and DNS
are full CRUD.

**Scope:**
- `Setup__CloudFront` with all five verbs (delete waits for
  distribution disable + deploy completion — long-running)
- `Setup__ACM` with check + status only (create/update/delete refuse)
- `Setup__DNS` with all five verbs (wildcard ALIAS only — per-slug
  records stay with the existing `Vault_App__Auto_DNS` and
  `register` path)
- Schemas for each
- CLI verbs

**Acceptance:**
```
sg vault-publish setup acm check                    # checks cert presence + region + domain
sg vault-publish setup cf check                     # full distribution check
sg vault-publish setup dns check                    # wildcard check
sg vault-publish setup cf update                    # if drift detected
```

**Owner:** Dev. Size: ~2.5 days. CF is the longest because of the
disable-and-wait dance on delete.

---

## Phase B4 — `setup check` aggregator + `bootstrap` rewrite (SMALL)

**Goal:** the unified check works end-to-end, and `bootstrap` is
rewritten on top of the per-area primitives.

**Scope:**
- `Setup__Service.check_all()` runs every area's check (in parallel
  where independent) and returns `Schema__Setup__Report`
- `Setup__Service.converge()` — replaces today's `bootstrap()`;
  iterates per-area `create` in the right dependency order
- `Setup__Service.teardown()` — new verb; iterates per-area `delete`
  in reverse order, with strong gating
- `Cli__Setup`: `sg vault-publish setup check`,
  `sg vault-publish bootstrap` (now calls `converge`),
  `sg vault-publish teardown` (new)
- The old `Vault_Publish__Service.bootstrap` becomes a thin
  delegation to `Setup__Service.converge` (or is deleted, with
  the CLI moved to the new shape)
- Phase A's `ensure_*` methods get deleted

**Acceptance:**
```
sg vault-publish setup check                              # one-shot report
sg vault-publish bootstrap                                # builds on per-area create
sg vault-publish bootstrap                                # idempotent on re-run
SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 \
  sg vault-publish teardown                                # removes everything
```

**Owner:** Dev. Size: ~1 day.

---

## Phase C — Optional: S3 layer bucket area (FUTURE, only if needed)

**Goal:** support the osbot-aws-style layer-via-S3 deployment if/when
the bundled zip outgrows the 50 MB direct-upload limit.

**Trigger:** waker zip + bundled deps > 40 MB (safety margin).
Today: ~10 MB. Plenty of headroom.

**Owner:** deferred.

---

## Phase ordering rationale

```
A   (small)   Bandage so bootstrap stops crashing TODAY
B1  (medium)  Skeleton + IAM (cleanest area; sets the pattern)
B2  (medium)  Lambda + URL (subsumes Phase A's bandage)
B3  (medium)  CF + ACM + DNS (slowest area = CF)
B4  (small)   Aggregator + bootstrap rewrite + teardown
C   (future)  S3, only if zip outgrows direct upload
```

Phase A and Phase B1 can land in parallel — A is a 1-hour fix, B1 is
a new sub-package. The bandage costs nothing because B2 deletes it
anyway.

## Cancel points

After A: bootstrap is unblocked. Operators can keep using it.
After B1: IAM drift is detectable; everything else still uses the
old code path.
After B4: the design is complete. New AWS resources (S3, etc.) can
be added later without re-architecting.

## What does not get built

- A state file (Terraform-style). AWS is the truth.
- Plan/apply two-phase commits. Direct AWS calls only.
- Multi-account / multi-region orchestration. One target at a time.
- Web UI for setup status. JSON output → consumer's choice.
- Anything in `sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py`
  beyond the new `setup` sub-command and the rewritten `bootstrap`.
  Runtime verbs (`register`, `unpublish`, etc.) untouched.

## Definition of done — at the end of phase B4

A reviewer (you) can run, on any AWS account/region:

```
sg vault-publish setup check                   # see exactly what's missing / drifted
sg vault-publish bootstrap                     # converge
sg vault-publish setup check                   # confirm all OK
sg vault-publish setup iam update              # apply a policy change targeted
sg vault-publish setup check                   # confirm IAM now OK
SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 \
  sg vault-publish teardown                    # remove everything cleanly
```

…with full confidence that every step is idempotent and observable.
