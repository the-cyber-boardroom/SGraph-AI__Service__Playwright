# Reality — v0.1.31 (+ agent_mitmproxy v0.1.32 sibling) — 2026-04-20

**Source of truth for what exists today.** Agents must update the relevant file in this folder whenever code changes.

> **Canonical location:** `team/roles/librarian/reality/v0.1.31/`. Earlier `v0.1.29__what-exists-today.md` single-file doc is superseded and kept only until the next Librarian pass removes it.

The reality doc was split into per-concern files this cycle (previously a single ~170-line file). Split reasons: easier to edit one section without re-reading the whole thing; lets the new `agent_mitmproxy/` sibling have its own file without bloating the Playwright surface doc; natural boundary for what each role touches (Architect → schemas, QA → tests, DevOps → docker/CI).

---

## Index

1. [`01__playwright-service.md`](01__playwright-service.md) — Playwright service surface: public + admin endpoints, service classes, schemas, consts.
2. [`02__agent-mitmproxy-sibling.md`](02__agent-mitmproxy-sibling.md) — **NEW in v0.1.32.** Sibling package at repo root (`agent_mitmproxy/`). Admin FastAPI, mitmweb addons, Docker image + ECR helpers, EC2 spin-up script.
3. [`03__docker-and-ci.md`](03__docker-and-ci.md) — Docker images + CI workflows (Playwright + mitmproxy).
4. [`04__tests.md`](04__tests.md) — Unit / integration / deploy test inventory by area.
5. [`05__proposed.md`](05__proposed.md) — What does NOT exist yet (aspirations, deferred work).

---

## Summary

**Phase 1 complete + Phase 2 largely complete + v0.1.13 clean-state milestone + v0.1.23 proxy-auth fix + v0.1.24 stateless-surface refactor + v0.1.29 first-pass agentic refactor + v0.1.31 two-Lambda provisioning + EC2 spike + v0.1.32 agent_mitmproxy sibling package.**

- **Playwright API surface: 18 endpoints** — 10 public + 8 `/admin/*` (unauthenticated, read-only). Unchanged from v0.1.29.
- **Playwright service classes: 10 of 10 live.** Unchanged from v0.1.24.
- **agent_mitmproxy admin API: 6 endpoints** — 2 health + 2 CA + 1 config + 1 UI-proxy. API-key-gated.
- **agent_mitmproxy addons: 2** — `Default_Interceptor` (request-id + timing stamps), `Audit_Log` (NDJSON to stdout).
- **Unit tests: 395 (Playwright, unchanged) + 34 passing + 1 skipped (agent_mitmproxy).**

## Changes since v0.1.29

### Playwright (v0.1.30 → v0.1.31)
- `scripts/provision_ec2.py` — throwaway EC2 spike to reproduce the Firefox/WebKit-on-Lambda hang. t3.large AL2023, UserData installs Docker + pulls the ECR image + runs with `FAST_API__AUTH__API_KEY__*` + `SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000`. Idempotent IAM role + SG; `--terminate` to tear down. Tests under `tests/unit/scripts/test_provision_ec2.py`.
- IAM role `sg-playwright-ec2-spike` gained `AmazonSSMManagedInstanceCore` (drop into a shell via `aws ssm start-session`; no SSH).
- SG name corrected (`sg-` prefix dropped — AWS reserves `sg-*` for SG IDs).
- SG description stripped of the em dash (AWS rejects non-ASCII `GroupDescription`).
- `scripts/provision_lambdas.py` — two-Lambda provisioning (`sg-playwright-baseline-<stage>` + `sg-playwright-<stage>`) with `--mode={full, code-only}`. `code-only` skips the ~30–60 s image-pull wait on Python-only refreshes.
- `ci-pipeline.yml::detect-changes` narrowed to `sgraph_ai_service_playwright/docker/images/**` (was `docker/**`); touching deploy-time `Build__Docker__*` helpers no longer forces an image rebuild.
- `ci-pipeline.yml::provision-lambdas` job replaces the old `deploy-code` single-track mode; picks `full` vs `code-only` from the `build-and-push-image` result.

### Sibling package (v0.1.32 — new)
See [`02__agent-mitmproxy-sibling.md`](02__agent-mitmproxy-sibling.md).

---

## Naming Convention

- Historical single-file reality docs: `v{version}__what-exists-today.md` (superseded from v0.1.31 onward).
- Split reality docs: `v{version}/{NN}__{slice}.md` under `team/roles/librarian/reality/`.
- The folder's `README.md` is the index.
