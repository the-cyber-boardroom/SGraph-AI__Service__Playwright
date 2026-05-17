# security — Proposed

PROPOSED — does not exist yet. Cross-cutting security work pending across the codebase.

Last updated: 2026-05-17 | Domain: `security/`
Sources: distributed from `_archive/v0.1.31/05__proposed.md` + host-control / cli proposed lists + DNS slice known-gaps.

---

## P-1 · Lockdown layers / declared narrowing

**What:** `declared_narrowing` ships as `[]` on `/admin/capabilities` today. Populate with actual narrowing claims (no internet without proxy, no eval outside allowlist, no boto3 outside `*__AWS__Client`, …).

Cross-references `playwright-service/proposed P-3`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-2 · WebSocket shell hardening (host-control)

**What:** `WS /shell/stream` has no per-message ratelimit, no idle timeout, no audit log, no resource cap. Hostile clients could spawn long-running processes that survive WS close.

Cross-references `host-control/proposed P-1`.

**Source:** `host-control/proposed/index.md`.

## P-3 · RBAC / capability vocabulary for host-control + Playwright tokens

**What:** Today a single shared API key gates the entire surface. Per-action capabilities (`host.read`, `host.containers.write`, `host.shell.execute`, `host.shell.stream`; analogous for playwright) would let one key be screenshot-only, another sequence-only, etc.

Cross-references `host-control/proposed P-2` + `playwright-service/proposed P-11`.

**Source:** Same brief as host-control P-1; v0.1.24 deferred list.

## P-4 · Larger `SHELL_COMMAND_ALLOWLIST`

**What:** The current 15-entry allowlist suffices for diagnostics but cannot cover legitimate ops (e.g. `journalctl -u <service>`, `top -bn1`, `vmstat`). Each addition requires AppSec sign-off.

Cross-references `host-control/proposed P-6`.

**Source:** `host-control/proposed/index.md`.

## P-5 · Per-route API-key scoping in Playwright service

**What:** v0.1.24 deferred. Today a single `FAST_API__AUTH__API_KEY__VALUE` gates everything. A capability-style token would let one key be screenshot-only, another sequence-only.

Cross-references `playwright-service/proposed P-11`.

**Source:** v0.1.24 deferred list.

## P-6 · Sidecar enforcement layer

**What:** Guarantee `agent_mitmproxy` is up before the Playwright service accepts requests. Today the sidecar comes up alongside via `docker compose` but there is no health-gate.

Cross-references `playwright-service/proposed P-6`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-7 · SSO / federated auth for mitmweb UI

**What:** Today `Routes__Web` exposes mitmweb through the API-key-gated admin API; the Basic `--proxyauth` mitmweb enforces is independent. No SSO; spike-grade creds only.

Cross-references `agent-mitmproxy/proposed P-6`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-8 · Auth-protected Prometheus scrape bridge

**What:** App metrics from Playwright/mitmproxy need an auth bridge (Prometheus `Authorization` vs `X-API-Key`).

Cross-references `agent-mitmproxy/proposed P-8`.

**Source:** `_archive/v0.1.31/05__proposed.md`.

## P-9 · Cert sidecar — `sg playwright vault re-cert --hostname <fqdn>`

**What:** §12 ADDENDUM of the DNS slice. **Q9 PENDING** — DNS-01 vs HTTP-01 for the cert sidecar. The cert-warning info block printed by `records add` points at a command that does not exist.

Cross-references `vault/proposed P-4` + `cli/proposed P-15`.

**Source:** `_archive/v0.1.31/16__sg-aws-dns-and-acm.md` known-gaps.

## P-10 · Auth beyond `X-API-Key` (UI + control plane)

**What:** No OAuth, no per-user identity, no SSO. Cross-references `ui/proposed P-8` + `cli/proposed P-10`.

**Source:** Slice 13/14 UI not-included lists.

## P-11 · Vault-sourced sidecar API key rotation

**What:** Follow-on to BV2.9. The host-control plane's API key is provisioned via env var on the EC2 instance today. Sourcing it from vault enables rotation without re-provisioning.

Cross-references `vault/proposed P-2`.

**Source:** `sg-compute/index.md` PROPOSED.
