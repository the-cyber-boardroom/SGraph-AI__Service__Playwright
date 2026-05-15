# Implementation Plan

PR-sized phases. Each ends with a green test suite or a working demo. The phasing
deliberately adds **one new class of risk per phase** (principle 10).

---

## Phase 0 — docs (no code)

The Dev session expands docs `01`–`09` of this pack from the Architect's grounding
into full briefs in the established shape, and the Architect reviews them. No code
in any `vault_publish/` package exists at the end of Phase 0.

**Done when:** docs reviewed and approved; the pack README sign-off checklist's
docs items are checked.

---

## Phase 1 — routing, always-on (prove the wildcard)

Goal: a manually-registered slug serves its vault over HTTPS through CloudFront,
with the instance always running. No waking, no provisioning-from-untrusted-input.

| Step | Work |
|------|------|
| 1.1 | `vault_publish` package skeleton: `schemas/`, `service/`, `fast_api/`, `cli/`, empty `__init__.py`, `version`. |
| 1.2 | `Safe_Str__Slug`, `Slug__Validator`, `Reserved__Slugs`, the `Enum__*` set. Table-driven tests. |
| 1.3 | `Slug__Resolver` — the deterministic derivation (stub against the SG/Send contract until open question #1 is answered; real once it is). |
| 1.4 | DevOps: one-time wildcard DNS + ACM cert + CloudFront distribution (see `09__dev-ops`). |
| 1.5 | Routing from `<slug>.sgraph.app` to an always-on per-slug EC2 (VPC origin). |
| 1.6 | `sg vp register`, `sg vp status`, `sg vp list`, `sg vp health` + their FastAPI routes. |

**Demo:** `sara-cv.sgraph.app` serves the `sara-cv` vault over HTTPS. `sg vp health`
green on all four infra layers.

**New risk introduced:** none beyond standard infra.

---

## Phase 2a — wake-on-demand, simple form

Goal: a stopped slug, hit cold, becomes live within minutes; warm requests served.
CloudFront's dynamic origin is the waker Lambda (FastAPI); the Lambda resolves,
wakes, and proxies.

| Step | Work |
|------|------|
| 2a.1 | `Vault__Fetcher` — fetch the immutable vault folder from `send.sgraph.ai`. |
| 2a.2 | `Manifest__Verifier` — signature verification against the billing-record key. **Reject path tested first.** |
| 2a.3 | `Manifest__Interpreter` — allowlisted-vocabulary mapping; unknown fields rejected. |
| 2a.4 | `Instance__Manager` — idempotent start/stop/status via `osbot-aws`; idle-timer arm/re-arm reusing the `sg lc` pattern. |
| 2a.5 | `Control_Plane__Client` — single-use key generation + IMDSv2 delivery + control-plane provisioning; setup endpoint closes after. |
| 2a.6 | `Publish__Service.wake` — composes the wake sequence (`04__routing` §4). |
| 2a.7 | `Waker__Lambda__Adapter` — the thin CF ⇄ FastAPI translation; deploy the FastAPI app behind the Lambda Web Adapter as a Function URL. |
| 2a.8 | The auto-refreshing warming page (`no-cache`). |
| 2a.9 | CloudFront points its dynamic origin at the waker Lambda. |

**Demo:** stop the `sara-cv` instance; hit the URL cold; warming page shows; live
within ~minutes; refresh serves the vault. Tamper with a manifest signature →
wake rejected, no instance started.

**New risk introduced:** provisioning from externally-sourced input. **Gated by
AppSec sign-off on `06__security` and open questions #2 and #4.**

---

## Phase 2b — wake-on-demand, optimised (deferred, spike-gated)

Goal: warm traffic bypasses the Lambda. Introduce CloudFront origin groups +
edge origin selection.

| Step | Work |
|------|------|
| 2b.0 | **Spike:** measure the Phase 2a warm-path Lambda hop cost. If acceptable, Phase 2b may be deferred indefinitely. |
| 2b.1 | **Spike:** resolve per-slug primary origin selection (`04__routing` §3 — the three options). |
| 2b.2 | Origin group: primary = per-slug EC2 VPC origin, secondary = waker Lambda. Tune connection timeout (~2 s, 1 attempt). |
| 2b.3 | Edge origin selection per the spike outcome. |

**Demo:** warm-path latency benchmarked below the Phase 2a baseline; cold path
still wakes correctly.

**New risk introduced:** (option-dependent) Lambda@Edge global surface — kept
minimal per principle 6.

---

## Phase 3 — CLI completeness + first real deployment

| Step | Work |
|------|------|
| 3.1 | `sg vp unpublish`, `sg vp wake`, `sg vp resolve` + routes. |
| 3.2 | First real vault live on `sgraph.app` — the medical-partner POC or the friend's CV vault (upstream brief acceptance criterion #10). |
| 3.3 | Reality doc updated in the same PR — `vault_publish` added to `team/roles/librarian/reality/`. |
| 3.4 | Debrief filed under `team/claude/debriefs/`, indexed. |

**Demo:** one real, owner-published vault serving on `sgraph.app`.

---

## Acceptance criteria (mapped to the upstream brief)

| Upstream # | Criterion | Phase |
|------------|-----------|-------|
| 1 | `*.sgraph.app` resolves via wildcard DNS to CloudFront | 1 |
| 2 | Wildcard ACM cert covers `*.sgraph.app` | 1 |
| 3 | Slug operational (create/read/delete association) | 1 (register/status/list), 3 (unpublish) |
| 4 | Edge resolves slug → vault; different subdomains serve different vaults | 1 (routing), 2a (via derivation) |
| 5 | Registering a slug yields a working URL within minutes | 2a |
| 6 | Unpublish removes the association | 3 |
| 7 | Vault updates propagate automatically | 2a (boot-time re-fetch) |
| 8 | Slug naming rules enforced | 1 |
| 9 | Reserved slug list blocks common service names | 1 |
| 10 | First real deployment live | 3 |
| 11 | sgraph.ai migrated to this infrastructure | post-MVP — split into its own phase with a rollback story (Architect note on the upstream brief) |

---

## Estimated effort

Rough, single Dev: Phase 1 ≈ 3–4 days, Phase 2a ≈ 4–5 days, Phase 2b ≈ 2–3 days
(spike-dependent), Phase 3 ≈ 2 days. Phase 0 ≈ half a day. The cross-repo open
questions are the real schedule risk, not the code.
