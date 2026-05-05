# v0.2.x — Backend (BV2.x phases)

**Audience:** the backend Sonnet team
**Prerequisites:** read [`../v0.2.0__sg-compute__architecture/`](../v0.2.0__sg-compute__architecture/) in full first (00 → 01 → 02 → 03).

This folder is a **per-phase brief**. Each `BV2_NN__*.md` file is self-contained: read it, do it, ship one PR, move on. **One phase per PR. One PR per session.** No big-bang refactors.

Branch naming: `claude/bv2-{N}-{description}-{session-id}`.
PR title: `phase-BV2.{N}: {short summary}`.

---

## Phase index (execution order)

| # | File | Theme | Blocks |
|---|------|-------|--------|
| BV2.1 | [`BV2_1__delete-orphan-host.md`](BV2_1__delete-orphan-host.md) | Delete orphan legacy `sgraph_ai_service_playwright__host/` | — |
| BV2.2 | [`BV2_2__section-sidecar.md`](BV2_2__section-sidecar.md) | Build `Section__Sidecar` user-data composable; wire into all 12 specs | — |
| BV2.3 | [`BV2_3__pod-manager.md`](BV2_3__pod-manager.md) | `Pod__Manager` + `Routes__Compute__Pods` | FV2.7 |
| BV2.4 | [`BV2_4__routes-nodes-cleanup.md`](BV2_4__routes-nodes-cleanup.md) | Refactor `Routes__Compute__Nodes` (no logic, no raw dicts, no mocks) | — |
| BV2.5 | [`BV2_5__create-node-and-lambda.md`](BV2_5__create-node-and-lambda.md) | `EC2__Platform.create_node` + `POST /api/nodes` + `control_plane/lambda_handler.py` | FV2.5 |
| BV2.6 | [`BV2_6__per-spec-cli.md`](BV2_6__per-spec-cli.md) | Per-spec `cli/` + `sg-compute spec <id> <verb>` dispatcher | — |
| BV2.7 | [`BV2_7__migrate-tier1-cli.md`](BV2_7__migrate-tier1-cli.md) | Migrate `__cli/{aws,core,catalog,image,ec2 schemas}` → `sg_compute/` | BV2.10, BV2.11 |
| BV2.8 | [`BV2_8__ci-guard-and-typesafe-fix.md`](BV2_8__ci-guard-and-typesafe-fix.md) | CI guard forbidding new tree → legacy imports; fix `: object = None` Type_Safe bypass | — |
| BV2.9 | [`BV2_9__migrate-vault.md`](BV2_9__migrate-vault.md) | Migrate `__cli/vault/` → `sg_compute/vault/` | — |
| BV2.10 | [`BV2_10__fold-sp-cli-fastapi.md`](BV2_10__fold-sp-cli-fastapi.md) | Fold `Fast_API__SP__CLI` into `control_plane/` with `/legacy/` mount | BV2.11 |
| BV2.11 | [`BV2_11__lambda-cutover.md`](BV2_11__lambda-cutover.md) | Lambda packaging cutover; delete legacy `sgraph_ai_service_playwright/` | — |
| BV2.12 | [`BV2_12__cleanup-mitmproxy-and-shims.md`](BV2_12__cleanup-mitmproxy-and-shims.md) | Delete `agent_mitmproxy/`; shim 8 legacy `__cli/<spec>/` dirs | — |
| BV2.13 | [`BV2_13__spec-layout-normalisation.md`](BV2_13__spec-layout-normalisation.md) | Normalise all 12 specs to canonical layout; lock `Enum__Spec__Capability` comment | — |
| BV2.14 | [`BV2_14__spec-test-coverage.md`](BV2_14__spec-test-coverage.md) | Add Routes + Service tests to every spec; drop `unittest.mock.patch` | — |
| BV2.15 | [`BV2_15__sidecar-security-hardening.md`](BV2_15__sidecar-security-hardening.md) | Cookie `HttpOnly=true`; CORS origin allowlist; `Routes__Host__Auth` test coverage | — |
| BV2.16 | [`BV2_16__storage-spec-integration.md`](BV2_16__storage-spec-integration.md) | Storage spec category + `s3_server` cross-repo discovery test | — |
| BV2.17 | [`BV2_17__delete-container-aliases.md`](BV2_17__delete-container-aliases.md) | Delete `/containers/*` sidecar aliases (after FV2.8 ships) | After FV2.8 |
| BV2.18 | [`BV2_18__testpypi-publish.md`](BV2_18__testpypi-publish.md) | TestPyPI publish + `RELEASE.md` | After all above |
| BV2.19 | [`BV2_19__spec-ui-static-files.md`](BV2_19__spec-ui-static-files.md) | `StaticFiles` mount in `Fast_API__Compute` serving `sg_compute_specs/<id>/ui/` at `/api/specs/<id>/ui/` | After BV2.13; **blocks FV2.6** |

---

## Phase ordering rationale

- **BV2.1-BV2.6** close the audit gaps (orphan, sidecar baseline, Pod__Manager, route cleanup, generic create, per-spec CLI). **Frontend FV2.x phases unblock progressively as these land.**
- **BV2.7-BV2.12** dismantle the dual-write trees in dependency order. BV2.7 + BV2.8 break the spec→legacy import cycle; the deletes follow.
- **BV2.13-BV2.14** raise the bar on spec quality (canonical layout, real test coverage, no mocks).
- **BV2.15** locks the sidecar security model — Architect must lock the cookie + CORS decisions before this starts.
- **BV2.16-BV2.18** deliver the v0.2 strategic adds: storage-spec category, alias cleanup post-frontend, public PyPI release validation.
- **BV2.19** adds `StaticFiles` mount infrastructure so FV2.6 (per-spec UI co-location) can proceed. Gracefully no-ops for specs with no `ui/` folder — safe to ship before any spec migrates its UI.

---

## Cross-cutting rules (binding every phase)

- Type_Safe everywhere. One class per file. Empty `__init__.py`.
- Routes have no logic. Pure delegation.
- `osbot-aws` for AWS. No direct boto3.
- **No mocks, no patches** in tests under `sg_compute__tests/` — use in-memory composition.
- 80-char `═══` headers on every Python file.
- No docstrings — single-line inline comments only where the WHY is non-obvious.
- Update reality doc in same commit; pointer to `team/roles/librarian/reality/changelog.md`.
- Each PR ends with a debrief in `team/claude/debriefs/`.

---

## When you start a session

1. `git fetch origin dev && git merge origin/dev`.
2. Read this README; pick the next un-shipped phase from the index above.
3. Open the phase file.
4. Verify any "Blocks" / "Blocked by" relationships in the index above.
5. Open a feature branch; ship the phase; debrief.
