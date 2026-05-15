# Vault-Publish — Dev Briefing Pack

**Pack version:** v0.2.11
**Pack date:** 2026-05-14
**Author:** Architect (Claude Code session)
**Audience:** Dev (lead), DevOps, QA, Librarian, Architect (review)
**Status:** PROPOSED — nothing described here exists yet. Cross-check against the reality doc.
**Branch base:** `dev`
**Feature branch:** `claude/review-subdomain-workflow-bRIbm`
**Upstream brief:** `v0.27.38__dev-brief__sgraph-app-subdomain-registration-workflow` (SG/Send project)

---

## One-paragraph summary

`sgraph.app` is registered. This pack defines **`vault-publish`** — a new top-level
package in this repo that turns a published, read-only SG/Send vault into a live
website at `https://<slug>.sgraph.app/` with one command. A wildcard DNS record and
a wildcard ACM certificate point every `*.sgraph.app` subdomain at a single
CloudFront distribution. Each slug maps — **deterministically, with no routing
database** — to an SG/API Transfer-ID and read key by reusing the existing
"simple token" mechanism. The vault content fetched from SG/API drives the
**declarative** provisioning of a per-slug EC2 instance that lives in a private
subnet (no public IP). Instances are woken on demand: CloudFront fails over to a
small Lambda that starts the instance and serves an auto-refreshing "warming up"
page; the instance arms an idle-shutdown timer and stops itself when traffic
stops. The Lambda is **as small as possible** — it is a thin adapter in front of
the same `vault-publish` FastAPI app the CLI uses, so one set of service classes
backs the CLI, the API, and the edge.

---

## Why this pack exists

The upstream brief (`v0.27.38`) defined the *capability*. Three rounds of Architect
review with the project lead refined it into a *buildable* design and closed the
two questions the upstream brief left open:

1. **No routing KV.** The original brief conceded a "small slug → share-token
   key-value lookup". The refined design removes even that: a slug is
   deterministically converted (server-side) into an SG/API Transfer-ID + read
   key, reusing the existing simple-token mechanism. The only per-slug state is
   the **billing record**, which already exists (slug validation was first
   introduced for billing).
2. **The arbitrary-code-execution hole is closed.** The upstream brief proposed
   running "whatever setup-scripts are inside the vault folder" — which directly
   contradicts `.claude/CLAUDE.md` rules #10 and #11. The refined design is
   **declarative**: the vault carries a manifest the EC2 control-plane interprets
   against an allowlisted vocabulary; the manifest is signature-verified before it
   is acted on; SG/API files are immutable so a derived location cannot be
   overwritten. Arbitrary scripts are the explicit last resort, gated by
   Architect + AppSec sign-off.

This pack is self-contained. A Dev session reading only this folder has everything
needed to start Phase 0.

---

## The shape, in one diagram

```
  sgit publish --slug sara-cv        (SG/Send CLI — a CLIENT of our API, not in this repo)
        │
        ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  vault-publish  (NEW top-level package in this repo)                 │
  │                                                                      │
  │   Tier 1  service classes  — pure Type_Safe, no Typer / no edge      │
  │   Tier 2  FastAPI routes   — thin delegation to Tier 1               │
  │   Tier 3a CLI verb tree    — `sg vp ...`  (thin Typer wrapper)        │
  │   Tier 3b waker Lambda     — thinnest CF-origin → FastAPI adapter,    │
  │                              SAME FastAPI app deployed inside it     │
  └──────────────────────────────────────────────────────────────────────┘

  Request path:

   browser → https://sara-cv.sgraph.app/
        │
        ▼
   Route 53  *.sgraph.app  ──►  CloudFront (one distribution, wildcard ACM cert)
        │
        ▼
   CloudFront origin selection
        ├─ instance up   ─────────────────────►  per-slug EC2 (private subnet, VPC origin)
        └─ instance down ─►  waker Lambda (FastAPI)
                                   │  derive(slug) → Transfer-ID + read key
                                   │  fetch vault folder from send.sgraph.ai
                                   │  verify manifest signature
                                   │  StartInstances (idempotent)
                                   │  control-plane provision (declarative manifest)
                                   └─ returns auto-refresh "warming up (~20s)" page
```

---

## Locked decisions

These are settled by the Architect ↔ project-lead conversation that produced this
pack. The Dev session implements against them. If any seems wrong, raise an
Architect-review request — do not silently change them.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **New top-level `vault_publish` package** in this repo, with the same API + CLI + classes structure as everything else. Three tiers: pure service classes, FastAPI routes, CLI verb tree — plus a thin waker-Lambda adapter that fronts the same FastAPI app. | "Same api, cli and classes as everything else." One service layer, three callers. Mirrors the CLI/FastAPI duality already established in the repo. |
| 2 | **Wildcard DNS + wildcard ACM, one CloudFront distribution.** `*.sgraph.app` plus `*.qa.sgraph.app`, `*.dev.sgraph.app`, `*.main.sgraph.app` as separate single-label wildcard SANs / CNAMEs. | DNS never changes per slug — no propagation wait. One cert, one distribution. |
| 3 | **No routing KV.** Slug → `(Transfer-ID, read key)` is a deterministic server-side derivation reusing the existing simple-token mechanism. The only per-slug state is the **billing record** (already exists). | Removes a whole persistence layer. The billing record is the integrity anchor (owner binding + signing public key reference). |
| 4 | **SG/API files are immutable.** | Removes the write-hijack threat: a predictable, derivable location cannot be overwritten by an attacker. |
| 5 | **Provisioning is declarative.** The vault folder carries a manifest the EC2 control-plane FastAPI *interprets* against an allowlisted vocabulary. Arbitrary scripts are the explicit last resort — Architect + AppSec sign-off + logged decision required. | `.claude/CLAUDE.md` rules #10, #11. Trust a constrained vocabulary, not `bash setup.sh`. |
| 6 | **The provisioning manifest is signature-verified by the waker before it is acted on — in MVP, not deferred.** Signing key referenced from the billing record. | Trust the payload, not the location. A signature check is the line between "attacker can run provisioning on our infra" and "attacker writes bytes we ignore". |
| 7 | **Control-plane auth = random, single-use, per-instance key.** Generated by the waker, delivered via EC2 user-data / IMDSv2 (never CF-facing). The control-plane setup endpoint closes after provisioning completes. | Blast radius = one instance, for the setup window only. No standing shared secret. |
| 8 | **CloudFront VPC origins — vault EC2s run in a private subnet, no public IPv4.** | Public IPv4 is now billed; private origins remove the cost, the IP-churn-on-stop/start problem, and a slice of attack surface. |
| 9 | **One EC2 per slug for MVP.** Generic AMI; vault content pulled at boot from SG/API. | Inherits the slim-AMI principle (`SPEC-slim-ami-s3-nvme`) — nothing large baked into the snapshot, no EBS lazy-load tax. |
| 10 | **Idle → stop reuses the existing `sg lc` shutdown-timer pattern.** Instance arms a timer on boot; the waker re-arms it on each cold hit. | Reuse, not reinvention. The pattern already exists in this repo. |
| 11 | **Wake-on-demand via CloudFront origin failover.** Primary origin = the live path; secondary origin = the waker Lambda Function URL. CF origin connection timeout tuned low (≈2 s, 1 attempt) so failover is fast. | Documented scale-from-zero pattern. The waker both *starts* the instance and *serves* the warming page. |
| 12 | **The waker Lambda is "as small as possible".** It is the `vault-publish` FastAPI app behind the Lambda Web Adapter; the only Lambda-specific code is the CF/Function-URL ⇄ HTTP translation. | Same single-image philosophy as the rest of the repo. The Lambda has no business logic — it calls FastAPI routes. |
| 13 | **MVP source = vaults / files published to `send.sgraph.ai`.** VPC-restricted vault access and S3-direct vault access are noted as future hardening. | Smallest first version; the immutability + signing model already gives a defensible posture. |
| 14 | **All AWS calls go through `osbot-aws`** — Route 53, ACM, EC2, CloudFront. No direct `boto3` (the narrow Function-URL two-statement exception aside). | `.claude/CLAUDE.md` stack rule. |
| 15 | **Region-in-hostname (`slug.eu-west-1.sgraph.app`) is deferred** past the single-region MVP. | Each region label is another single-label wildcard SAN, and region routing multiplies the waker topology (a regional waker per region). Additive later — does not need to be designed in now. |

---

## Phasing

| Phase | Scope | Done when |
|-------|-------|-----------|
| **Phase 0** | Dev expands docs `01`–`09` from this pack's grounding into full briefs; Architect reviews. **No code.** | Docs reviewed and approved. |
| **Phase 1** | Wildcard DNS + ACM cert + one CloudFront distribution + VPC-origin routing to an **always-on** instance. Prove routing only. | A manually-registered slug serves its vault over HTTPS through CloudFront. |
| **Phase 2a** | Wake-on-demand, **simple form**: CloudFront's dynamic origin is the waker Lambda (FastAPI). FastAPI resolves the slug, wakes the instance if needed, and proxies to it once up. Accept the extra hop. | A stopped slug, hit cold, is live within ~minutes; warm requests served. |
| **Phase 2b** | Wake-on-demand, **optimised**: introduce CloudFront origin groups + edge origin selection so warm traffic hits the EC2 directly and the waker is only the cold-path secondary. Deferred until the Phase 2a hop cost is measured. | Warm-path latency benchmarked; edge routing spike resolved (see `04`). |
| **Phase 3** | `sg vp` CLI surface complete; first real deployment (medical-partner POC or the friend's CV vault); reality doc updated. | One real vault live on `sgraph.app`. |

---

## File index

| File | Purpose | Status |
|------|---------|--------|
| `README.md` *(this file)* | Status, summary, locked decisions, phasing, open questions, sign-off | ✅ Architect |
| `00__pack-overview/quick-reference.md` | One-page reference of the core concepts and terms | ✅ Architect |
| `01__principles/principles.md` | The principles that govern every design decision in this pack | ✅ Architect |
| `02__architecture/architecture.md` | The four-layer infrastructure + the three-tier code architecture | ✅ Architect |
| `03__cli/cli-surface.md` | The `sg vp` verb tree and the FastAPI route surface | ✅ Architect |
| `04__routing/edge-and-routing.md` | Wildcard DNS/cert, CloudFront, origin failover, VPC origins, the edge-routing spike | ✅ Architect |
| `05__provisioning/provisioning-and-manifest.md` | Slug derivation, SG/API fetch, the declarative manifest, control-plane provisioning | ✅ Architect |
| `06__security/security-model.md` | Immutability, signing, isolation, the single-use key, residual-risk statement | ✅ Architect |
| `07__schemas/schemas-and-modules.md` | Type_Safe schemas, Enum/Safe primitives, the module tree | ✅ Architect |
| `08__implementation-plan/implementation-plan.md` | PR-sized phases, milestones, acceptance criteria | ✅ Architect |
| `09__dev-ops/dev-ops-brief.md` | One-time wildcard setup, CloudFormation vs Terraform, ACM renewal, CI | ✅ Architect |
| `appendices/A__glossary.md` | Every term in this pack, defined | ✅ Architect |

---

## Open questions for the SG/Send Architect

These cross the repo boundary — `vault-publish` lives here, but the vault, the
simple-token mechanism, the billing record, and `sgit publish` live in SG/Send.
None blocks Phase 0 or Phase 1; all block Phase 2a.

1. **The derivation function.** Confirm the exact slug → `(Transfer-ID, read key)`
   mechanism and reconcile its input charset with the slug naming rules (3–40
   chars, lowercase, digits, hyphens).
2. **The billing record as integrity anchor.** Confirm it can carry the slug →
   owner binding and the signing public key (or a reference to it).
3. **`send.sgraph.ai` fetch path.** Confirm the endpoint the waker uses to fetch a
   vault folder by Transfer-ID + read key, and whether VPC-restricted access is
   available as later hardening.
4. **Manifest signing at publish time.** Who holds the signing private key, and
   how does `sgit publish` sign the manifest when the vault is published?

---

## Sign-off checklist (Architect → Dev handoff)

Before the Dev session starts Phase 1, this must be all-checked:

- [ ] All 15 locked decisions accepted
- [ ] The 5-phase plan accepted
- [ ] The 4 open questions answered by the SG/Send Architect (blocks Phase 2a, not Phase 1)
- [ ] AppSec has reviewed `06__security/security-model.md` and accepted the residual-risk statement
- [ ] Branch `claude/review-subdomain-workflow-bRIbm` is current with `dev`
- [ ] Dev has expanded docs `01`–`09` and an Architect review has approved them
- [ ] No code in a `vault_publish/` package exists yet (Phase 0 is docs-only)

---

## Status updates

| Date | Note |
|------|------|
| 2026-05-14 | Pack filed by Architect, synthesising three rounds of review on upstream brief `v0.27.38`. Awaiting Dev pickup of Phase 0. |
