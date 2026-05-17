# agent-mitmproxy — Proposed

PROPOSED — does not exist yet. Items below extend the agent_mitmproxy sibling but are not in code today.

Last updated: 2026-05-17 | Domain: `agent-mitmproxy/`
Source: distributed from `_archive/v0.1.31/05__proposed.md` ("agent_mitmproxy (v0.1.32 — phase 1 ships the scaffolding only)" section).

---

## P-1 · `POST /config/interceptor`

**What:** Upload / replace the live interceptor script. The read-only `GET /config/interceptor` landed in phase 1; the write-side + reload is phase 2.

**Required:**

- Body validation through `Schema__Interceptor__Source` (already exists).
- A reload primitive — either a SIGHUP to mitmweb or a management endpoint (cross-references P-6 below).
- Atomic write to `PATH__CURRENT_INTERCEPTOR` so a half-written script is never picked up.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-2 · `Build__Docker__Agent_Mitmproxy` helper class

**What:** The Playwright equivalent (`Build__Docker__SGraph_AI__Service__Playwright`) stages the build context in a tempdir and shells the Docker SDK directly to bypass osbot-docker's `@catch` wrapper. The mitmproxy CI workflow currently shells `docker build` inline with repo-root context — no staging class exists.

**Required:**

- New `Build__Docker__Agent_Mitmproxy` matching the Playwright equivalent's surface.
- `tests/docker/test_Build__Docker__Agent_Mitmproxy.py` + `test_ECR__Docker__Agent_Mitmproxy.py` deploy-via-pytest harness.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-3 · Container-level smoke test

**What:** CI builds + pushes the image but does not pull it back and exercise the admin API. Add a `tests/integration/` smoke that boots the container locally and asserts `/health/info` returns the expected `service_version`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-4 · End-to-end proxy-auth CI test

**What:** Requested in the v0.1.24 deferred list. The mitmproxy image is the obvious vehicle for this sidecar but no CI wiring exists yet.

**Required:** a CI job that brings up Playwright + agent_mitmproxy together, hits a real proxy-protected URL, and asserts the request transited via the sidecar.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-5 · EC2 deploy via CI

**What:** Intentionally out of scope for phase 1. `scripts/provision_mitmproxy_ec2.py` (now `scripts/provision_ec2.py`, unified) runs on-demand from an operator laptop; no `workflow_dispatch` hook calls it yet.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-6 · Auth-protected mitmweb UI / SSO

**What:** Today `Routes__Web` exposes the UI through the API-key-gated admin API, but the Basic `--proxyauth` that mitmweb itself enforces is independent. No SSO / federated auth; spike-grade creds only.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-7 · Addon registry hot-reload

**What:** The mitmweb process is restarted by supervisord on crash, but the addon list is not reloadable at runtime. Would need a SIGHUP handler or a management endpoint.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-8 · Prometheus auth bridge

**What:** Scraping app metrics from Playwright/mitmproxy via Prometheus requires bridging `X-API-Key` vs Prometheus `authorization`. Infrastructure metrics (cadvisor, node-exporter) already scrape cleanly. App metrics accessible manually via `sg-ec2 metrics`.

**Source:** `_archive/v0.1.31/05__proposed.md`.
