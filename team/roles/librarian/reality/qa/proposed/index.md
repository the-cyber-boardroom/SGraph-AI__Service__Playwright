# qa — Proposed

PROPOSED — does not exist yet. Items below extend the test surface but are not in code today.

Last updated: 2026-05-17 | Domain: `qa/`
Sources: distributed from `_archive/v0.1.31/05__proposed.md` + per-slice known-gaps.

---

## P-1 · Deploy-via-pytest for `sp-playwright-cli` Lambda

**What:** Numbered tests (`test_1__ensure_role`, `test_2__build_push_image`, …) mirroring `tests/deploy/`. Today only unit tests cover the deploy classes.

**Source:** `_archive/v0.1.31/08__sp-cli-lambda-deploy.md` known-gap 1. Mirrors `cli/proposed P-12` and `infra/proposed P-8`.

## P-2 · `__to__main` / `__to__prod` deploy tests

**What:** v0.1.24 deferred. Today the dev-stage deploy chain is covered; main+prod are not.

**Source:** v0.1.24 deferred list (via `_archive/v0.1.31/05__proposed.md`).

## P-3 · Smoke tests asserting `/admin/*`

**What:** Deploy-via-pytest smoke tests still point at the 10 public endpoints; the 8 admin endpoints (`/admin/health`, `/admin/info`, …) added in v0.1.29 are not yet asserted.

**Source:** `_archive/v0.1.31/04__tests.md` "Integration + deploy — unchanged from v0.1.24".

## P-4 · `tests/integration/` for agent_mitmproxy

**What:** CI builds + pushes the mitmproxy image but does not pull it back and exercise the admin API. Container-level smoke test needed. Cross-references `infra/proposed P-5`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-5 · End-to-end proxy-auth CI test

**What:** Bring up Playwright + agent_mitmproxy together and assert a real proxy-protected URL transits via the sidecar. Cross-references `infra/proposed P-6`.

**Source:** v0.1.24 deferred list.

## P-6 · Playwright / pytest end-to-end UI smoke tests

**What:** No end-to-end UI tests today for the dashboard. This is the Playwright service — using its own engine to test the UI would be neat. Cross-references `ui/proposed P-6`.

**Source:** Slice 13/14/15 not-included lists.

## P-7 · Full TestClient coverage for linux / docker routes

**What:** Slice 13 added mounting tests only (path-set membership). The route handlers themselves don't have TestClient coverage like the catalog / elastic / observability / vnc routes do.

**Source:** Slice 13 not-included list.

## P-8 · Cleanup of botocore failure in slice 13 suite

**What:** "Total suite: 1176 passing (1 pre-existing botocore failure unrelated to this slice)" — the 1 failing test should be identified and fixed.

**Source:** `_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md` final line.
