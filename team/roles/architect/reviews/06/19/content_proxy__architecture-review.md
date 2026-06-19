---
title: "Architect Review — content_proxy (sg cp) spec: plan vs implementation"
file: content_proxy__architecture-review.md
author: Architect (Claude)
date: 2026-06-19
version: v0.2.63
status: REVIEW — post-MVP assessment of the as-built content_proxy spec. No code changes; findings + recommendations for human ratification.
scope: sg_compute_specs/content_proxy/ (39 modules, ~2,016 LoC non-test, 93 unit tests, 30 commits)
parent:
  - library/docs/specs/v0.2.63__content-transformation-proxy-stack.md
  - team/roles/architect/reviews/06/18/v0.2.63__content-transformation-proxy/   (the brief pack)
  - team/roles/librarian/reality/content-proxy/index.md
---

# Architect Review — `content_proxy` (`sg cp`)

> **Verdict: solid MVP, ships its core promise — but the test pyramid is inverted
> and the spec has drifted from the as-built.** The stack assembles 3 external
> images + a new EC2 spec and is confirmed working end-to-end live (vault UI,
> `/pw` routing, proxy chain, self-signed TLS). The architecture is clean and
> reuses the shared foundation well. The cost: ~8 defects were caught **live**,
> not by tests, because there is no integration layer — and several were
> avoidable by mirroring `sg va` field-by-field up front.

---

## 1. Plan vs built

The brief pack planned slices 0–10. As-built:

| Slice | Planned | Built | Notes |
|-------|---------|-------|-------|
| 0 skeleton/schemas/manifest | ✓ | ✅ | conformant; discovered by convention |
| 1 interceptor (pure logic + active.py) | ✓ | ✅ | clean stdlib/adapter split |
| 2–4 compose (2 proxies + mitm + pw + vault) | ✓ | ✅ | + cert-init for TLS |
| 5 CLI (8 verbs + extras) | ✓ | ✅ | builder-driven + `local`/`smoke` |
| 6 TUI | screens + source | ⚠ **partial** | render fns only; no live `__TUI__Source`, no Textual screens |
| 7 traffic corpus + report | ✓ | ✅ | pure grade/report; live runner is a thin stub |
| 8 EC2 + deploy-via-pytest | ✓ | ⚠ **partial** | EC2 launch ✅; **deploy-via-pytest not written** |
| 9 vault loading (zip/sgit) | post-MVP | ❌ | schemas only, no `Vault__Loader` |
| 10 reality/docs | ✓ | ✅ | reality doc current |
| — TLS (LE/self-signed via cert-init) | follow-up | ✅ **pulled forward** | not in the original slice plan |
| — `/pw` runtime injection | (assumed env-var) | ✅ **re-derived live** | see §4 |

Net: the **MVP (0–8) is functionally complete and live-verified**; the test/observability slices (deploy-via-pytest, live TUI) and post-MVP vault loading are open.

---

## 2. Architecture — what's right

- **Boundary discipline holds.** The spec layers mirror the canonical `docker`/`vault_app` shape: `Compose__Template` (pure render) · `User_Data__Builder` (pure render) · `Stack__Mapper` (boto3 dict → schema) · `AWS__Client` (composes the **shared** `EC2__*` helpers) · `Service` (orchestrator). No new `boto3`; the shared foundation is reused exactly as `sg va` does. ✅
- **Type_Safe / Safe_* / Enum / one-class-per-file** are followed throughout. No raw-primitive schema fields; all fixed sets are `Enum__*`. ✅
- **The interceptor split is the best decision in the codebase.** `Content_Proxy__Interceptor__Logic` is stdlib-only and fully unit-tested; `active.py` is the thin mitmproxy adapter. This is what made 17 interceptor/logic tests possible without mitmproxy. ✅
- **Pure-render + drift-guard.** The committed `docker-compose.yml` is generated from the template and a test asserts no drift — a genuinely good pattern. ✅
- **Configurability is principled** — `proxy_tool` (mitmweb/mitmdump), `tls` (none/self-signed/letsencrypt/acm), `--env-file` verbatim, `--ca-from-local`. Each maps to a clear schema/enum.

---

## 3. Architecture — divergences & debt

| # | Finding | Severity | Recommendation |
|---|---------|----------|----------------|
| D1 | **Cross-spec import.** `content_proxy` imports `Vault_App__Reverse_Proxy__Override` (+ `SERVE_WITH_PROXY`) from the `vault_app` spec. Sister specs are not meant to cross-import. | **High** | Extract the override + entrypoint to a shared home (e.g. `sg_compute/fast_api/reverse_proxy/` or a `_shared/`), or land the upstream `SGraph-AI__App__Send` PR so `/pw` is native (kills the injection entirely). |
| D2 | **No `api/routes/`.** The new-spec contract (`v0.2.6__authoring-a-new-top-level-spec.md`) expects `Routes__ContentProxy__Stack`; the manifest even declares `create_endpoint_path=/api/specs/content_proxy/stack`. There is no route class → the control-plane HTTP surface + dashboard card don't exist. | **Med** | Either add the routes (parity with `docker`/`vault_app`) or explicitly declare `content_proxy` CLI-only and drop the `create_endpoint_path` claim. |
| D3 | **Health overridden to SSM.** `Service.health()` replaces the base external-HTTP probe with a localhost-via-SSM probe (~30 lines duplicated). Justified (SG/IP/self-signed), but it's per-spec divergence. | Low | Consider promoting an `ssm_health` helper to `Spec__Service__Base` so other ephemeral-TLS specs reuse it. |
| D4 | **Secrets in user-data + tags.** The access token + (optionally) AWS creds are baked into `/opt/content-proxy/.env` via user-data, and the access token is stored in an EC2 tag (`cp:access-token`) — both IMDS/describe-readable. Matches `sg va`'s `AccessToken` tag, accepted for MVP. | Med (security) | Track the hardening: instance-role for S3 (drop baked creds), SSM Parameter Store for the access token, in the post-MVP slice. |
| D5 | **Auth surface is a three-token maze.** `FASTAPI_API_KEY_*` (interceptor↔mitm-service), the access token (`FAST_API__AUTH__API_KEY__VALUE` == `SGRAPH_SEND__ACCESS_TOKEN`, vault+`/pw`), and `--proxyauth` (mitmproxy-ext). This caused two live defects. | Med | Publish a one-page **auth map** (who-signs-what) in the spec; it's the highest-confusion area. |

None of D1–D5 are blockers; D1 and D2 are the ones that should not calcify.

---

## 4. Failure analysis (debrief convention)

The live-iteration log is the most important architectural signal. **~8 defects reached the operator's screen before any test caught them:**

**Bad failures (surfaced live, not by tests):**
1. MITM image missing `httpx` (external image, but no pre-flight smoke).
2. Interceptor mount path `./interceptors` vs `../../interceptors` (compose-relative).
3. CA dir mounted read-only (mitmproxy couldn't self-gen).
4. `max_hours` typed `int` while the builder passes `float`.
5. SSM `run_command` timeout `20 < 30` (AWS minimum).
6. **`/pw` not mounted** — the spec assumed the stock image honours `FAST_API__REVERSE_PROXY__ROUTES`; it doesn't. `sg va` already solved this with runtime injection. *This is the headline miss.*
7. Auth token mismatch (`SGRAPH_SEND__ACCESS_TOKEN` vs `FAST_API__AUTH__API_KEY__VALUE`).
8. Vault published `443:443` while the container serves `:8080` (NONE).

**Root cause (architectural):** the spec **referenced** `sg va` but the implementation **re-derived** the vault wiring (env var names, `/pw` mechanism, vault port, TLS) instead of mirroring the as-built `Vault_App__Compose__Template` field-by-field. Every one of #6–#8 was already answered there.

**Good failures:** the pure-logic/render split made fixes cheap and each was test-locked on the way out (drift guard, `sg_rules`, `parse_http_code`, `localhost_probe_command`, etc.). The recovery loop was fast — the problem is it ran in *production*, not CI.

**Architect lesson (record in the decisions log):** *When a new spec assembles an existing image that another spec already drives, the contract is "diff against the proven `Compose__Template`," not "re-specify from the brief."*

---

## 5. Test pyramid — the central gap

93 tests, **100% pure unit** (render output, mappers, pure logic). There is **no integration tier**: no docker-compose bring-up, no real-Chromium transform assertion, no deploy-via-pytest. The brief pack's L5 (transform correctness) and the numbered EC2 lifecycle were specified and **not built**.

Consequence: the unit tests assert *what we render*, never *what runs*. All 8 defects above live in the gap between those two. This is the single highest-leverage fix.

---

## 6. Spec drift

The spec (`v0.2.63__content-transformation-proxy-stack.md`) predates the live work and no longer matches the as-built on: the **access-token auth model**, **`/pw` runtime injection** (vs env-var), **cert-init TLS** (self-signed/letsencrypt-ip + the SG `:80` rule), **SSM health**, and the **`local`/`smoke`/`ca` CLI surface**. The reality doc was kept current; the spec was not. **Reconcile the spec to as-built** (Architect owns "spec vs code wins" — here code won, repeatedly, so the spec must catch up).

---

## 7. Recommendations (prioritized)

1. **P1 — Build the integration tier.** A gated `docker compose up` smoke (`/mitm-proxy` + `/pw/health` + a transform fixture) + the numbered deploy-via-pytest. This retro-covers defects #1–#8 and is the MVP's missing safety net.
2. **P1 — Kill the cross-spec import (D1).** Shared module or the upstream Send PR for native `/pw`.
3. **P2 — Reconcile the spec to as-built (§6)** and publish the **auth map (D5)**.
4. **P2 — Decide `api/routes` (D2):** build them or drop the control-plane claim.
5. **P3 — Security hardening slice (D4):** instance-role S3 + SSM-param token; remove baked secrets.
6. **P3 — Finish the TUI** (live `__TUI__Source` + screens over the existing render fns) and **vault loading** (P-6) when the product needs them.

---

## 8. Bottom line

For an MVP gluing three external services into a new ephemeral-EC2 spec, this is **above the bar**: clean boundaries, real reuse, principled configurability, and a working live stack. It is **not yet production-grade**: no integration tests, a cross-spec dependency, a drifted spec, and an MVP-grade secret model. Close P1 (integration tier + the cross-spec import) before this pattern is copied for the next assembled-image spec — those two are what turn "works on the operator's screen" into "works, and stays working."
</content>
