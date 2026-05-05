# v0.2.1 Hotfix — Backend

**Audience:** the backend Sonnet team (the dev who shipped BV2.1-BV2.10 + BV2.19).
**Read first:** [`../../v0.2.0__sg-compute__architecture/00__README.md`](../../v0.2.0__sg-compute__architecture/00__README.md), then the executive review at [`../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md`](../../../humans/dinis_cruz/claude-code-web/05/05/10/00__executive-review__v0.2-implementation.md).

**Stop all new BV2.x phase work until Tier 1 is closed.**

---

## Phase index

### Tier 1 — Security hotfix bundle (ONE PR, security review)

Ship all 6 in **one PR** titled `phase-T1__BE-security-hotfix`. Branch `claude/t1-be-hotfix-{session-id}`. The PR description lists each fix with file:line evidence. Add a security-review note.

| # | File | What it fixes |
|---|------|---------------|
| T1.1 | [`T1_1__fast-api-compute-base-class.md`](T1_1__fast-api-compute-base-class.md) | `Fast_API__Compute` extends plain `Fast_API` (every `/api/*` route unauthenticated) |
| T1.2 | [`T1_2__remove-privileged-flag.md`](T1_2__remove-privileged-flag.md) | `Section__Sidecar` runs `--privileged` (NOT in brief) |
| T1.3 | [`T1_3__api-key-via-ssm.md`](T1_3__api-key-via-ssm.md) | API key plaintext in EC2 user-data, readable via IMDS |
| T1.4 | [`T1_4__post-api-nodes-auth.md`](T1_4__post-api-nodes-auth.md) | `POST /api/nodes` unauthenticated AND launches sidecars with empty key |
| T1.5 | [`T1_5__pod-manager-per-node-key.md`](T1_5__pod-manager-per-node-key.md) | `Pod__Manager` env-var key vs per-node key — Pods tab will 401 in production |
| T1.6 | [`T1_6__boot-time-auth-assertion.md`](T1_6__boot-time-auth-assertion.md) | Legacy SP-CLI surface fails open if env unset; no boot assertion |

### Tier 2 — Contract violations (one PR each, in this order)

| # | File | What it fixes |
|---|------|---------------|
| T2.1 | [`T2_1__create-node-podman-vnc.md`](T2_1__create-node-podman-vnc.md) | BV2.5 created docker only; brief required 3 specs (docker + podman + vnc) |
| T2.2 | [`T2_2__firefox-cli.md`](T2_2__firefox-cli.md) | BV2.6 built docker CLI; brief explicitly named **firefox** as target |
| T2.3 | [`T2_3__object-none-cleanup-and-ci-guard.md`](T2_3__object-none-cleanup-and-ci-guard.md) | ~39 `: object = None` sites survived; CI guard not wired into GH workflow |
| T2.4 | [`T2_4__real-vault-writer.md`](T2_4__real-vault-writer.md) | BV2.9 vault writer is fake-200 stub; URL `/vault/vault/spec/...` (double "vault"); routes return raw dicts |
| T2.5 | [`T2_5__lambda-web-adapter.md`](T2_5__lambda-web-adapter.md) | Mangum used in `lambda_handler.py`; project mandates AWS Lambda Web Adapter |
| T2.6 | [`T2_6__safe-str-primitives.md`](T2_6__safe-str-primitives.md) | Raw `str` / `int` parameters in `Section__Sidecar`, `Pod__Manager`, `Schema__Node__Create__Request__Base` |
| T2.7 | [`T2_7__strip-docstrings.md`](T2_7__strip-docstrings.md) | 6 docstrings introduced in BV2.6 (`Cli__Compute__Spec.py`, `Cli__Docker.py`) |

### Tier 3 — Integration cleanup (one PR each)

| # | File | What it fixes |
|---|------|---------------|
| T3.1 | [`T3_1__bv2.19-packaging-fix.md`](T3_1__bv2.19-packaging-fix.md) | BV2.19 `*/ui/**/*` glob in wrong pyproject; UI files won't ship to Lambda |
| T3.2 | [`T3_2__pod-manager-stats-and-info.md`](T3_2__pod-manager-stats-and-info.md) | FV2.7 only migrated `list` + `logs`; `/pods/{name}` and `/pods/{name}/stats` still cross-origin |

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
