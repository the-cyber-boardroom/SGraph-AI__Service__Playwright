# Quick Reference

One page. Read after the pack `README.md`, before the deeper docs.

---

## The core concepts

| Term | One-line definition |
|------|---------------------|
| **Slug** | A human-chosen subdomain label, e.g. `sara-cv` in `sara-cv.sgraph.app`. |
| **Derivation** | The deterministic, server-side function `slug → (Transfer-ID, read key)`, reusing SG/Send's existing simple-token mechanism. No lookup table. |
| **Billing record** | The only per-slug state. Already exists (slug validation was introduced for billing). Holds slug → owner binding + signing public key reference. The integrity anchor. |
| **Vault folder** | The immutable file/folder fetched from SG/API by `(Transfer-ID, read key)`. Contains the site content **and** the provisioning manifest. |
| **Provisioning manifest** | A declarative document inside the vault folder. The EC2 control-plane FastAPI interprets it against an allowlisted vocabulary. Signature-verified before use. |
| **Per-slug instance** | One EC2 per slug, in a private subnet, no public IP. Generic AMI; pulls its vault content at boot. |
| **Waker** | A small Lambda — the `vault-publish` FastAPI app behind the Lambda Web Adapter. CloudFront's failover origin. Starts the instance, provisions it, serves the warming page. |
| **Control-plane** | The FastAPI already added to every instance this repo creates. The waker drives provisioning through it, authenticated with a single-use key. |

---

## The three code tiers + one adapter

```
  Tier 1   vault_publish service classes   pure Type_Safe, no Typer, no edge awareness
  Tier 2   FastAPI routes                  thin delegation to Tier 1
  Tier 3a  CLI verb tree  (`sg vp ...`)     thin Typer wrapper over Tier 2 / Tier 1
  Tier 3b  waker Lambda                     thinnest CF ⇄ HTTP adapter; runs the SAME FastAPI app
```

One service layer. Three callers. The waker has **no business logic** — it invokes
FastAPI routes.

---

## The four infrastructure layers

```
  1  Route 53      *.sgraph.app wildcard → CloudFront      (set once)
  2  ACM           wildcard cert *.sgraph.app (+ env SANs)  (set once, auto-renews)
  3  CloudFront    one distribution; origin failover         (set once)
  4  Per-slug EC2  private subnet, VPC origin, woken on demand
```

---

## Request lifecycle (cold)

1. Browser hits `https://sara-cv.sgraph.app/`.
2. Route 53 wildcard → CloudFront.
3. Primary origin (the stopped instance) is unreachable → CloudFront fails over to the waker Lambda.
4. Waker parses `sara-cv` from the Host header.
5. Waker derives `(Transfer-ID, read key)` from the slug.
6. Waker fetches the immutable vault folder from `send.sgraph.ai`.
7. Waker **verifies the manifest signature** (key from the billing record). Reject → stop.
8. Waker `StartInstances` (idempotent — check state first; the call returns immediately).
9. Waker calls the instance control-plane with a single-use key + the declarative manifest.
10. Waker returns an auto-refreshing "warming up (~20 s)" page, `no-cache`.
11. Instance boots, applies the manifest, arms its idle-shutdown timer, becomes healthy.
12. Next request: CloudFront routes to the live instance.

## Request lifecycle (warm)

Browser → Route 53 → CloudFront → live per-slug EC2 (VPC origin). No Lambda in
the path (Phase 2b) or one cheap proxy hop (Phase 2a).

---

## What is NOT being built

- No routing key-value store (derivation replaces it).
- No per-slug DNS record (the wildcard covers everything).
- No per-slug certificate (the wildcard cert covers everything).
- No arbitrary script execution (declarative manifest; scripts are a gated last resort).
- No region-in-hostname routing yet (deferred past single-region MVP).
- No custom-domain support (paid-tier future; same routing mechanism, different host).

---

## The rules this pack must not break

- `.claude/CLAUDE.md` #10 / #11 — no arbitrary code execution; allowlist-gated.
- `.claude/CLAUDE.md` #14 — AWS via `osbot-aws`, never raw `boto3`.
- All classes extend `Type_Safe`; zero raw primitives; one class per file; no Literals.
- Routes have no logic — pure delegation to the service layer.
