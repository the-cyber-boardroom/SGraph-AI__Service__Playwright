# Debriefs — Index

Chronological list of implementation debriefs. Most recent first.

| Date       | Commit(s)                  | Slice                                           | File |
|------------|----------------------------|-------------------------------------------------|------|
| 2026-04-19 | 0bdecab, 298f9e1, 450a8d5, dfee003, 69f0d4e, e094adc | **v0.1.29 — First-pass agentic refactor.** Env-var rename `SG_PLAYWRIGHT__* → AGENTIC_*`; new L1/L2 subpackages `agentic_fastapi/` + `agentic_fastapi_aws/`; one-command `scripts/deploy_code.py` (package → S3 → Lambda env → smoke); 8 read-only `/admin/*` endpoints (Agentic_Admin_API); SKILL files + `capabilities.json` stub; single-track CI with new `deploy-code` job. Public HTTP surface (10) + service classes (10) unchanged. Hotfix `e094adc` — swap raw boto3 for AWS_Config after first CI deploy-code run tripped `s3.region_name()` AttributeError. 390 unit tests green. | `2026-04-19__v0.1.29-first-pass-agentic-refactor.md` |
| 2026-04-17 | *(pending)*                | **v0.1.24 — Remove stateful session API, repurpose `/browser/*` as stateless one-shots.** Deletes `/session/*`, `/quick/*`, `Session__Manager`, `Action__Runner`; reimplements `/browser/*` as 6 stateless one-shot endpoints each accepting optional `browser_config` (incl. proxy); drops `session_id` + `close_session_after` from `Schema__Sequence__Request`. Endpoint count 25 → 10. Lambda-safe + security-safe by construction. | `2026-04-17__v0.1.24-remove-stateful-session-api.md` |
| 2026-04-17 | deb5c79                    | **QA session** — authenticated-proxy testing against dev Lambda; produced `qa-findings__proxy-testing.md` with P1 Bug #1 (CDP Fetch needed for proxy auth) + P1 Bug #4 (sync/async Playwright poisoning) + P3 Bug #3 (session leak on CF 504) + schema redesign proposal (`Schema__Proxy__Auth__Basic`). Drove the v0.1.14 reliability slice (deadline + watchdog). | `2026-04-17__qa-proxy-testing-findings.md` |
| 2026-04-17 | 906ba05 (preceded by 8922484, cdba60c, 22dd98a, 6869632) | **Milestone** — 100%-clean-state per call (per-call sync_playwright + Chromium, register/try-finally teardown) + per-phase timing breakdown surfaced (`Schema__Sequence__Timings`; JSON on `/quick/html` + `/sequence/execute`, `X-*-Ms` headers on `/quick/screenshot`); production-verified at ~800–1200 ms total | `2026-04-17__milestone-clean-state-per-call.md` |
| 2026-04-17 | 0f24354                    | Phase 2.9 — Step__Executor (NAVIGATE / CLICK / FILL / SCREENSHOT / GET_CONTENT / GET_URL; 10 deferred stubs) + Artefact__Writer.capture_* + CI env-var hotfix for integration job | `2026-04-17__phase-2.9-step-executor.md` |
| 2026-04-17 | 5184011                    | Phase 2.8 — Docker infra (Base + Build + ECR + Lambda + Local) + deploy-via-pytest (ECR push, local container, deploy to dev, smoke dev) | `2026-04-17__phase-2.8-docker-infra.md` |
| 2026-04-17 | 29be9d9                    | Phase 2.7 — FastAPI wiring (Playwright__Service orchestrator + Routes__Health + Fast_API__Playwright__Service; chassis-before-engine reorder) | `2026-04-17__phase-2.7-fastapi-wiring.md` |
| 2026-04-17 | 4ff12b2                    | Phase 2.6 — Browser__Launcher (real Chromium + env-var escape hatch; 5 integration tests live) | `2026-04-17__phase-2.6-browser-launcher.md` |
| 2026-04-17 | d4d8a53                    | Phase 2.5 — Credentials__Loader (vault ↔ browser-context glue; full spec source) | `2026-04-17__phase-2.5-credentials-loader.md` |
| 2026-04-17 | 4794f02                    | Phase 2.4 — Artefact__Writer (sink routing + vault JSON seams; capture_* deferred) | `2026-04-17__phase-2.4-artefact-writer.md` |
| 2026-04-16 | f6a4cfb                    | Phase 2.3 — Sequence__Dispatcher (parse surface; execute_step deferred) | `2026-04-16__phase-2.3-sequence-dispatcher.md` |
| 2026-04-16 | b9bbce3                    | Phase 2.2 — Session__Manager (v2 §4 callsites; v1 not in pack) | `2026-04-16__phase-2.2-session-manager.md` |
| 2026-04-16 | 571fd77                    | Phase 2.1 — Capability__Detector + ENV_VAR constants (spec §4.6, §7) | `2026-04-16__phase-2.1-capability-detector.md` |
| 2026-04-16 | 64dc249                    | Phase 1.4 — Request__Validator + JS__Expression__Allowlist (spec §9) | `2026-04-16__phase-1.4-request-validator.md` |
| 2026-04-16 | 4c63685                    | Phase 1.3 complete — §5.5–§5.10 + §6 + §8 + tests | `2026-04-16__phase-1.3-complete.md` |
| 2026-04-16 | 1f2edd6                    | Refactor — one-class-per-file (primitives, enums, schemas) | `2026-04-16__refactor-one-class-per-file.md` |
| 2026-04-16 | 8cb083c                    | CI fix — pytest exit-code-5 on placeholder jobs | `2026-04-16__ci-fix-exit-code-5.md` |
| 2026-04-16 | f219b01                    | CI fix — pin Playwright base image tag         | `2026-04-16__ci-fix-playwright-tag.md` |
| 2026-04-16 | 5ab4dc2, 68114e0           | CI fix — docker/deploy test placeholders + pytest install | `2026-04-16__ci-fix-docker-deploy-jobs.md` |
| 2026-04-16 | 0fa0f7f                    | Phase 1.3 (WIP) — core schemas §5.1–§5.4 + Safe_Str__Host | `2026-04-16__phase-1.3-wip-core-schemas.md` |
| 2026-04-16 | 3585724                    | Phase 1.1 + 1.2 — Safe_* primitives + Enum__* types | `2026-04-16__phase-1.1-1.2-primitives-enums.md` |
| 2026-04-16 | 08641a9                    | Phase 0 — bootstrap skeleton                    | `2026-04-16__phase-0-bootstrap.md` |
