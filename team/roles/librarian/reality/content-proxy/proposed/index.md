# content-proxy — Proposed

PROPOSED — does not exist yet. Items below extend `sg_compute_specs/content_proxy/` but are not in code today.

Last updated: 2026-06-18 | Domain: `content-proxy/`

---

## P-1 · EC2 launch Service — ✅ DONE (2026-06-18)

`Content_Proxy__Service` + `Content_Proxy__AWS__Client` now reuse the shared
`sg va`-style EC2 foundation (`EC2__SG/AMI/Instance/Launch/Tags__*` +
`Stack__Naming`). See the EXISTS section.

## P-2 · `Cli__Content_Proxy` (Spec__CLI__Builder wiring) — ✅ DONE (2026-06-18)

8 standard verbs via `Spec__CLI__Builder` + a `local up|down|status` group.
Registered as `sg content-proxy` / `cp`. Remaining CLI extras (`status`/`traffic`/
`transform`/`logs` reading a running stack) ride on P-3.

## P-3 · Textual screens + `Content_Proxy__TUI__Source`

The render functions exist (status/traffic). The live `__TUI__Source` (HTTP/SSM
polling of component health + mitmweb `/flows`) and the thin Textual screens
(`status`/`traffic`/`scripts`/`transform`/`logs`) are not built. Plus `scripts`
and `transform` render functions.

## P-4 · api/routes — `Routes__ContentProxy__Stack` + `…__Flows`

FastAPI route classes exposing the same operations. Blocked on P-1.

## P-5 · Integration + deploy-via-pytest

Real-Chromium transform-correctness (L5), the `/mitm-proxy` smoke against live
containers, and the numbered EC2 lifecycle (`test_1__create_stack` …). Gated on
docker / chromium / AWS creds.

## P-6 · Vault loading (post-MVP)

`Content_Proxy__Vault__Loader` (zip copy-in / sgit clone) + `load-vaults` verb +
roles 1–2 (script vault feeds the MITM service; append→S3 log vault). Schemas
(`Vault__Source`, `Vault__Kind`) already exist; the loader does not.

## P-7 · TLS provisioning (LE / ACM) on EC2

The `tls` field + the user-data `ca_block` exist; the actual Let's Encrypt
self-termination and ACM-on-ALB wiring reuse the existing aws-deployment / vault
TLS foundation — not yet wired here.
