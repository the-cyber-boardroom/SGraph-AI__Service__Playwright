# v0.2.1 Hotfix — Backend

**Audience:** the backend Sonnet team (the dev who shipped BV2.1-BV2.10 + BV2.19).
**Read first:** [`../../v0.2.0__sg-compute__architecture/00__README.md`](../../v0.2.0__sg-compute__architecture/00__README.md), then the executive review at [`../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md).

**Stop all new BV2.x phase work until Tier 1 is closed.**

---

## Phase index

Status as of 2026-05-05 14:30 UTC.

### Tier 1 — Security hotfix bundle (ONE PR, security review)

| # | File | Status |
|---|------|--------|
| T1.1 | [`T1_1__fast-api-compute-base-class.md`](T1_1__fast-api-compute-base-class.md) | ✅ DONE (commit `815b7c5`) |
| T1.2 | [`T1_2__remove-privileged-flag.md`](T1_2__remove-privileged-flag.md) | ✅ DONE (commit `815b7c5`) |
| T1.3 | [`T1_3__api-key-via-ssm.md`](T1_3__api-key-via-ssm.md) | ✅ DONE (commit `815b7c5`) |
| T1.4 | [`T1_4__post-api-nodes-auth.md`](T1_4__post-api-nodes-auth.md) | ✅ DONE (transitively, commit `815b7c5`) |
| T1.5 | [`T1_5__pod-manager-per-node-key.md`](T1_5__pod-manager-per-node-key.md) | ✅ DONE (commit `815b7c5`) |
| T1.6 | [`T1_6__boot-time-auth-assertion.md`](T1_6__boot-time-auth-assertion.md) | ✅ DONE (commit `815b7c5`) |

### Tier 2 — Contract violations

| # | File | Status |
|---|------|--------|
| T2.1 | [`T2_1__create-node-podman-vnc.md`](T2_1__create-node-podman-vnc.md) | ✅ DONE (commit `02d57ea`) |
| T2.2 | [`T2_2__firefox-cli.md`](T2_2__firefox-cli.md) | ⚠ PARTIAL textbook (commit `375f805`) — set-credentials + upload-mitm-script deferred to [`T2_2b__firefox-credentials-routes.md`](T2_2b__firefox-credentials-routes.md) |
| T2.3 | [`T2_3__object-none-cleanup-and-ci-guard.md`](T2_3__object-none-cleanup-and-ci-guard.md) | ✅ DONE (commits `c0f6bc5` + `b562ced` + `10fcbde`) — CI guard wired into actual GH workflow |
| T2.4 | [`T2_4__real-vault-writer.md`](T2_4__real-vault-writer.md) | 🔴 **STILL BROKEN** — commit `f8fbd52` shipped fake-stub 2.0; `vault_attached=False` in production wiring; route test bypasses prefix. **Fix in [`T2_4b__real-vault-writer-finish.md`](T2_4b__real-vault-writer-finish.md)** |
| T2.5 | [`T2_5__lambda-web-adapter.md`](T2_5__lambda-web-adapter.md) | ⚠ PARTIAL (commit `6dbff6f`) — Mangum imports gone; Dockerfile delta + AWS Lambda Web Adapter extension layer not in commit |
| T2.6 | [`T2_6__safe-str-primitives.md`](T2_6__safe-str-primitives.md) | ⚠ ~10% DONE (commit `2b30ff1`) — `Pod__Manager` named in brief, untouched; spec-side raw types untouched. **Finish in [`T2_6b__safe-str-primitives-finish.md`](T2_6b__safe-str-primitives-finish.md)** |
| T2.7 | [`T2_7__strip-docstrings.md`](T2_7__strip-docstrings.md) | ⚠ PARTIAL (commits `af65c2c` + `552e5cb`) — CLI + Spec__Loader covered; `Section__*` (7 files) + `Vnc__*` (3 files) still carry docstrings. **Finish in [`T2_7b__strip-docstrings-finish.md`](T2_7b__strip-docstrings-finish.md)** |

### Tier 3 — Integration cleanup

| # | File | Status |
|---|------|--------|
| T3.1 | [`T3_1__bv2.19-packaging-fix.md`](T3_1__bv2.19-packaging-fix.md) | ✅ DONE (commit `542cf08`) — packaging glob moved to `sg_compute_specs/pyproject.toml`; CI test added |
| T3.2 | [`T3_2__pod-manager-stats-and-info.md`](T3_2__pod-manager-stats-and-info.md) | ✅ DONE (commit `542cf08`) — `Pod__Manager.get_pod_stats` + `Routes__Compute__Pods` extended |

### Backend follow-up briefs (filed during execution)

| # | File | Origin |
|---|------|--------|
| BV (filed) | [`BV__ami-list-endpoint.md`](BV__ami-list-endpoint.md) | FE-T2.1 dependency |
| BV (filed) | [`BV__caller-ip-endpoint.md`](BV__caller-ip-endpoint.md) | FE-T2.5 dependency |
| BV (NEW) | [`BV__spec-readme-endpoint.md`](BV__spec-readme-endpoint.md) | FE-T2.2 known-broken README link |

### Backend follow-up patches (filed 2026-05-05 14:30)

| # | File | Why |
|---|------|-----|
| **T2.4b** | [`T2_4b__real-vault-writer-finish.md`](T2_4b__real-vault-writer-finish.md) | 🔴 Still broken in production; was fake-stub 2.0 |
| **T2.6b** | [`T2_6b__safe-str-primitives-finish.md`](T2_6b__safe-str-primitives-finish.md) | Pod__Manager + spec-side raw types |
| **T2.7b** | [`T2_7b__strip-docstrings-finish.md`](T2_7b__strip-docstrings-finish.md) | Section__* + Vnc__* still carry docstrings |
| **T2.2b** | [`T2_2b__firefox-credentials-routes.md`](T2_2b__firefox-credentials-routes.md) | Firefox CLI deferred verbs |

---

## Hard rules (binding every PR)

- Type_Safe everywhere; no Pydantic; no Literals; no `: object = None`.
- One class per file. Empty `__init__.py`.
- Routes have no logic — pure delegation.
- `osbot-aws` for AWS — no direct boto3.
- **No mocks, no patches** in tests.
- 80-char `═══` headers; no docstrings.
- Branch `claude/t1-be-hotfix-{session-id}` (Tier 1) or `claude/t2-be-{N}-{session-id}` / `claude/t3-be-{N}-{session-id}` (Tier 2/3).
- PR title `phase-T1__BE-security-hotfix` (Tier 1) or `phase-T2.{N}__BE: {summary}` / `phase-T3.{N}__BE: {summary}`.
- Update reality doc + changelog in same commit.
- Each PR ends with a debrief in `team/claude/debriefs/`.

## New process rules (apply from now on)

- **`PARTIAL` is a valid debrief status.** Any descope = follow-up brief in same PR.
- **CI guards wired in same PR as added.** No false-confidence guards.
- **"Stop and surface"** if you're working around a problem instead of fixing the root cause.
- **Live smoke test** as an acceptance criterion on every phase.
- **Commit messages match content.** No "all X" claims when half is done.

---

## Recommended execution order

1. **T1 bundle** (one PR, security review) — security comes first.
2. **T2.1 → T2.2 → T2.3 → T2.4 → T2.5 → T2.6 → T2.7** — contract violations in order of impact.
3. **T3.1 → T3.2** — cleanup.
4. Resume planned BV2.11+ sequence only after Tier 1 + Tier 2 close.

See [`SESSION_KICKOFF.md`](SESSION_KICKOFF.md) for the paste-into-fresh-session brief.
