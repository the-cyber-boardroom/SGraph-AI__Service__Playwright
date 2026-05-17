# infra — Proposed

PROPOSED — does not exist yet. Items below extend the infra surface but are not in code today.

Last updated: 2026-05-17 | Domain: `infra/`
Sources: distributed from `_archive/v0.1.31/05__proposed.md` plus deploy known-gaps.

---

## P-1 · Two-track CI pipeline split

**What:** Separate fast unit-test workflow from the full-build pipeline.

**Source:** `05__proposed.md` (Playwright section).

## P-2 · Docker Hub publishing of base images

**Source:** `05__proposed.md`.

## P-3 · Build helper for agent_mitmproxy (`Build__Docker__Agent_Mitmproxy`)

**What:** Cross-references `agent-mitmproxy/proposed P-2`. The Playwright equivalent stages the build context in a tempdir and shells the Docker SDK directly. Mitmproxy CI today shells `docker build` inline.

**Source:** `05__proposed.md` (agent_mitmproxy section).

## P-4 · `tests/docker/test_Build__Docker__Agent_Mitmproxy.py` + `test_ECR__Docker__Agent_Mitmproxy.py`

**What:** Deploy-via-pytest harness equivalent to the Playwright pipeline's.

**Source:** `05__proposed.md`.

## P-5 · Container-level smoke test for agent_mitmproxy

**What:** CI builds + pushes the image but does not pull it back and exercise the admin API.

**Source:** `05__proposed.md`.

## P-6 · End-to-end proxy-auth CI test (Playwright + sidecar)

**What:** Wire up a CI job that brings up Playwright + agent_mitmproxy together and asserts a real proxy-protected URL transits via the sidecar.

**Source:** v0.1.24 deferred list (carried via `05__proposed.md`).

## P-7 · EC2 deploy via CI for agent_mitmproxy

**What:** Intentionally out of scope for phase 1. `workflow_dispatch` hook calling `scripts/provision_ec2.py` to refresh the EC2 stack.

**Source:** `05__proposed.md`.

## P-8 · Live deploy-via-pytest for `sp-playwright-cli` Lambda

**What:** Today only unit tests cover the deploy classes. Numbered tests (`test_1__ensure_role`, `test_2__build_push_image`, …) mirroring `tests/deploy/` would catch CI-only regressions.

**Source:** `_archive/v0.1.31/08__sp-cli-lambda-deploy.md` known-gap 1. Mirrors `cli/proposed P-12`.

## P-9 · PyPI publishing of `agentic_fastapi` / `agentic_fastapi_aws`

**Source:** `05__proposed.md`.

## P-10 · CI mitmproxy sidecar for proxy-auth coverage

**What:** v0.1.24 deferred. The mitmproxy image is now the obvious vehicle; no wiring exists yet.

**Source:** v0.1.24 deferred list (via `05__proposed.md`).
