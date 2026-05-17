---
title: "07 — Domain strategy: aws.sg-labs.app for vault-publish (FLAT scheme)"
file: 07__domain-strategy.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00; rewritten 2026-05-17 after flat-scheme decision)
parent: README.md
status: PLAN — no code, no commits. Domain addendum to the vault-publish v2 plan. ALL key decisions resolved 2026-05-17.
---

# 07 — Domain strategy

> **DECIDED 2026-05-17.**
> - **Zone:** `aws.sg-labs.app` (delegated child of `sg-labs.app`; own hosted zone — verified live with 3 records: NS / SOA / ACM validation CNAME).
> - **Cert:** `*.aws.sg-labs.app` wildcard — ARN `arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa` (Issued).
> - **Scheme:** FLAT — `<slug>.aws.sg-labs.app`. No namespace concept in v2.
> - **Bootstrap:** singular, not per-namespace. One CloudFront distribution, one cert ARN, one Function URL.

The user registered `sg-labs.app`, delegated a child zone `aws.sg-labs.app`, and issued a wildcard cert for `*.aws.sg-labs.app`. This file pins the scheme, cert strategy, record lifecycle, and hosted-zone wiring against those facts.

The plan deliberately keeps the **existing** `sg-compute.sgraph.ai` zone untouched for the vault-publish substrate (`sg vault-app` per `Route53__AWS__Client.DEFAULT_ZONE_NAME_FALLBACK` at `sgraph_ai_service_playwright__cli/aws/dns/service/Route53__AWS__Client.py:35`). `aws.sg-labs.app` is **additive** — it becomes the canonical zone for the v2 vault-publish work via the existing `SG_AWS__DNS__DEFAULT_ZONE` env var.

The single most important consequence: the existing `default_zone_name()` resolver (`Route53__AWS__Client.py:38-39`) reads `SG_AWS__DNS__DEFAULT_ZONE`. The vault-publish work can switch zones by env var alone — zero code changes to the DNS layer.

---

## 1. Subdomain naming scheme

### 1.1 Decision: FLAT under `aws.sg-labs.app`

**Production form:** `<slug>.aws.sg-labs.app`

Where:

- `<slug>` is the existing `Safe_Str__Slug` primitive (regex `[a-z0-9\-]+`, max 40, charset enforced at construction — see `03__delta-from-lab-brief.md §A.7` and reuse-map row "Safe_Str__Slug").
- The apex `aws.sg-labs.app` and bare apex names are **reserved for platform control-plane records** (CloudFront wildcard ALIAS, ACM DNS-validation records, future status pages).

Worked examples:

| Operator command | Resulting FQDN |
|------------------|----------------|
| `sg vp register sara-cv` | `sara-cv.aws.sg-labs.app` |
| `sg vp register hello-world` | `hello-world.aws.sg-labs.app` |

### 1.2 Options considered (E / B / C / D rejected)

| # | Scheme | Why rejected |
|---|--------|--------------|
| A | `<slug>.sg-labs.app` (flat at root) | Reserves `sg-labs.app` itself for v2 — leaves no room for future delegated children (labs, etc.). |
| B | `<experiment>.sg-labs.app` (flat, lab-only) | Loses the slug abstraction; doesn't suit vault-publish. |
| C | `<slug>.<lab>.sg-labs.app` (two-level) | Wildcard cert needs care — `*.sg-labs.app` does NOT cover `<slug>.<lab>.sg-labs.app` (RFC 6125: wildcards cover one label). Would require multiple wildcard certs. |
| D | `<env>.<slug>.<...>` | Premature — no env story yet. |
| E | `<slug>.<namespace>.sg-labs.app` with `vp` / `lab` namespaces | Same RFC 6125 problem as C: existing single-label wildcard cert `*.aws.sg-labs.app` does NOT cover `<slug>.<namespace>.sg-labs.app`. Would invalidate the already-issued cert. |
| **FLAT** | **`<slug>.aws.sg-labs.app`** | **Chosen.** Single-label wildcard `*.aws.sg-labs.app` covers every leaf. Existing cert is good. Operationally trivial. |

### 1.3 Rationale

1. **Wildcard cert works.** `*.aws.sg-labs.app` covers `<slug>.aws.sg-labs.app` (single label below the wildcard parent). Cert already exists and is Issued — no operator-side cert work.
2. **One control-plane setup per environment.** One CloudFront distribution, one Function URL, one cert ARN — no per-namespace duplication.
3. **No namespace collisions to engineer around.** Lab spec (when it lands, post-v2) gets its **own** delegated zone (e.g., `lab.sg-labs.app`) with its **own** wildcard cert. Clean separation by zone, not by label.
4. **`Safe_Str__Slug` unchanged.** Slug validates the leaf only.
5. **`Reserved__Slugs` no longer carries namespace tokens** — `vp` / `lab` are not labels in the flat scheme. Reserved list is just hygiene words (`www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`) — see Q15 in `06__open-questions.md`.

### 1.4 Reconciliation with existing plan primitives

| Existing primitive | How it fits the flat scheme |
|--------------------|----------------------------|
| `Safe_Str__Slug` (per `02__reuse-map.md §5`) | Validates the **leaf** only. Unchanged. |
| `Slug__Validator` (reserved list + policy) | Unchanged — runs against the leaf. Seeded per Q15. |
| `Schema__Vault_Publish__Register__Request.fqdn` | Computed as `f'{slug}.aws.sg-labs.app'` (or `f'{slug}.{zone_apex}'` where `zone_apex = SG_AWS__DNS__DEFAULT_ZONE`). One-line inline in `Vault_Publish__Service.register`. No `Fqdn__Builder` class for v2. |
| `Route53__Zone__Resolver.resolve_zone_for_fqdn` | Already walks labels right-to-left; finds `aws.sg-labs.app` zone for any FQDN under it. No change. Verified — `Vault_App__Auto_DNS.run` (`sg_compute_specs/vault_app/service/Vault_App__Auto_DNS.py:70`) uses it. |
| `Slug__From_Host` (Waker — phase 2c) | Parses `Host:` header. Strips the apex `.aws.sg-labs.app` and validates the leaf with `Safe_Str__Slug`. Returns `Safe_Str__Slug` directly — **no `Schema__Subdomain__Parts` schema, no tuple**. |
| `DEFAULT_ZONE_NAME_FALLBACK` constant | Stays at `sg-compute.sgraph.ai` for `sg vault-app` substrate. Vault-publish v2 overrides via `SG_AWS__DNS__DEFAULT_ZONE=aws.sg-labs.app`. **Do NOT change the constant** — it's the substrate's default. |

### 1.5 No `Enum__Sg_Labs__Namespace`

**DELETED from the plan.** The flat scheme has no namespace concept. The lab spec, when it ships post-v2, gets its own delegated zone (`lab.sg-labs.app` or similar) and its own wildcard cert — separation by zone, not by intra-zone label.

---

## 2. Certificate strategy

### 2.1 Decision: consume the existing wildcard

| Field | Value |
|-------|-------|
| ARN | `arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa` |
| Covers | `*.aws.sg-labs.app` |
| Region | `us-east-1` (CloudFront requirement) |
| Status | Issued |
| Validation | DNS-01 CNAME present in `aws.sg-labs.app` zone (1 of 3 records) |
| Renewal | ACM-managed; auto-renews forever |

**Bootstrap consumes the ARN; does NOT mint** (decided 2026-05-17, Q7 = A):

```bash
sg vp bootstrap \
    --zone aws.sg-labs.app \
    --cert-arn arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa
```

The cert ARN gets stored in SSM at `/sg-compute/vault-publish/bootstrap/cert-arn` (matches `06__open-questions.md` Q10's SSM-only decision; no per-namespace segment under the flat scheme).

### 2.2 Schemes considered and rejected

| # | Scheme | Why rejected |
|---|--------|--------------|
| A | `*.sg-labs.app` | Does NOT cover `<slug>.aws.sg-labs.app` (one-label RFC 6125 rule). |
| B | Per-namespace `*.vp.sg-labs.app`, `*.lab.sg-labs.app` | The flat scheme has no namespace label; this would require switching back to scheme E. |
| C | Per-FQDN ACM cert, issued on `vp register` | Over-engineered; adds latency + ACM quota pressure. |
| D | SAN cert with multiple wildcards | Every namespace addition re-validates all SANs; fragile. |
| **CHOSEN** | **Single existing `*.aws.sg-labs.app` wildcard** | **One ARN to manage, auto-renewed by ACM, already Issued.** |

### 2.3 Region implications

- **CloudFront requires `us-east-1` ACM certs.** The wildcard lives in `us-east-1` regardless of the Waker Lambda's region (which is `eu-west-2` per the brief's defaults). Already correct.
- **The Waker Lambda's Function URL** auto-issues an AWS-managed TLS cert on `*.lambda-url.<region>.on.aws`. Operator-facing certs (the wildcard) only sit in front of CloudFront. The path is `client → CloudFront (us-east-1 cert) → Function URL (region-managed cert) → EC2 origin (per-FQDN LE cert via existing cert-init container)`.
- **ALB / API Gateway aren't in scope.** Brief uses Lambda Function URLs as the Waker origin.

### 2.4 What about the EC2-direct cert post-warm?

When the Waker drops out of the path (DNS swap from wildcard ALIAS-to-CloudFront to specific-A-to-EC2 IP — brief [`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) step 7), the browser hits the EC2 directly. The EC2 needs its own cert for `<slug>.aws.sg-labs.app` — **already** handled by the existing `cert-init` container with Let's Encrypt issuance (substrate confirmed by `01__grounding.md §1.4` user-data builder; verified live in Phase 0).

The wildcard ACM cert and the per-FQDN LE cert co-exist:

- Wildcard ACM cert → CloudFront edge → cold path.
- Per-FQDN LE cert → EC2 nginx → warm path.

Both serve traffic for the same FQDN, at different times in the slug's lifecycle. Neither blocks the other.

### 2.5 Forward note — labs land in a separate zone

When the lab spec eventually lands (post-v2, per `06__open-questions.md` Q1), labs get a **delegated zone** (e.g., `lab.sg-labs.app`) with their **own** wildcard cert (`*.lab.sg-labs.app` in `us-east-1`). Clean separation by zone — no name collisions with vault-publish slugs. Not v2 scope; parked as a forward note.

---

## 3. Route 53 record lifecycle

### 3.1 Inventory of record types per slug

For a fully-warm vault-publish slug `sara-cv`:

| Record | Type | TTL | Lifecycle | Owner |
|--------|------|-----|-----------|-------|
| `*.aws.sg-labs.app` | A ALIAS → CloudFront | n/a (alias) | Created at bootstrap. **Never deleted** during normal operation. | `Vault_Publish__Service.bootstrap` (phase 2d) |
| `sara-cv.aws.sg-labs.app` | A | 60 s | Created on `register` (after EC2 boot) **OR** on `start` (after stop→start). Deleted on `unpublish` **OR** on `stop`. | `Vault_App__Auto_DNS.run` (existing); deletion = new `delete_per_slug_a_record` helper in phase 1a |
| ACM DNS-01 validation | CNAME | ACM-managed | Created at cert-issuance time. Lives forever (ACM uses it for renewal). | Operator, once (already done) |

### 3.2 Who creates, who deletes

| Action | Reads | Writes | Service class |
|--------|-------|--------|---------------|
| `sg vp bootstrap` (phase 2d) | — | wildcard ALIAS A under `aws.sg-labs.app` | `Vault_Publish__Service.bootstrap` → `Route53__AWS__Client.upsert_a_alias_record` (`Route53__AWS__Client.py:216-221` — already exists, REUSE) |
| `sg vp register <slug>` (phase 1b) | wildcard ALIAS for verification | per-slug A record (after `vault-app create_stack` returns the IP) | `Vault_Publish__Service.register` → existing `Vault_App__Service.create_stack` (which internally calls `Vault_App__Auto_DNS.run`) |
| `sg vault-app stop <slug>` (phase 1a) | — | **deletes** the per-slug A record. **Does not** touch the wildcard. | `Vault_App__Service.stop_stack` → new `delete_per_slug_a_record` → `Route53__AWS__Client.delete_record` (`Route53__AWS__Client.py:205-214` — REUSE) |
| `sg vault-app start <slug>` (phase 1a) | — | **re-creates** the per-slug A record with the new public IP | `Vault_App__Service.start_stack` → reuses `Vault_App__Auto_DNS.run` (same code path as `create_stack`) |
| `sg vp unpublish <slug>` (phase 1b) | — | **deletes** per-slug A; **deletes** SSM registry entry; calls `vault_app.delete_stack` | `Vault_Publish__Service.unpublish` → composes the two existing services |
| Stack teardown by other means (e.g. ops kills the EC2 by hand) | — | **leaves** the per-slug A record orphaned | Operator-driven cleanup via `sg aws dns records delete` (see §3.4) |

### 3.3 TTL policy

- **Per-slug A records: 60 s.** Matches `Vault_App__Auto_DNS.AUTO_DNS__RECORD_TTL_SEC` (`Vault_App__Auto_DNS.py:27`). Short TTL is load-bearing — the Waker's "DNS swap after warm" relies on browsers picking up the specific A record within one TTL window. Do not raise.
- **Wildcard ALIAS: ACM/CF-managed.** Alias records have no caller-configurable TTL; CloudFront's edge cache rules apply.
- **ACM validation CNAMEs: ACM-managed.** Operator does not touch.

### 3.4 Stale-record reaper — DEFERRED (decided 2026-05-17, Q12)

**Defer to operator-driven cleanup.** The substrate already exposes `sg aws dns records delete <name>` (verified at `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py:1022-1054`) — operator can purge orphaned A records on demand.

A dedicated `sg vp reap` verb is **not** built in v2. Re-evaluate as a phase-2d-followup if orphan accumulation becomes painful.

### 3.5 Stack teardown contract — `delete_stack` audit (Q13, gating P1a)

Verified during this plan's preparation (`sg_compute_specs/vault_app/service/Vault_App__Service.py:528-546`): **`delete_stack` does NOT delete the per-slug A record.** It calls `instance.terminate` + `sg.delete_security_group`; never invokes `Route53__AWS__Client.delete_record` or `Vault_App__Auto_DNS` cleanup. Every `sg vault-app delete` to date has leaked an A record.

**Confirmed gating action (decided 2026-05-17, Q13):** P1a's first commit wires the deletion path into `delete_stack` using existing `Route53__AWS__Client.delete_record`. `stop_stack`'s DNS-delete then mirrors the reference path.

---

## 4. Hosted-zone wiring

### 4.1 Where the zone ID lives

**Recommendation: env var + late-binding resolver, NEVER in Git.**

Pattern, mirroring `Route53__AWS__Client.default_zone_name()` (line 38-39):

```bash
# Operator's environment for vault-publish v2 work:
export SG_AWS__DNS__DEFAULT_ZONE=aws.sg-labs.app
# (the zone ID is resolved lazily by name; operator never types it)
```

The **zone NAME** lives in env (`SG_AWS__DNS__DEFAULT_ZONE`). The **zone ID** is resolved lazily by name lookup (`Route53__AWS__Client.find_hosted_zone_by_name` at `Route53__AWS__Client.py:76-82` — exists, no change). The operator never types a zone ID.

### 4.2 Cross-account — DEFERRED (decided 2026-05-17, Q14)

**Out of scope for v2.** Single-account assumption (everything in the operator's default AWS account). Park in `library/roadmap/`.

### 4.3 What MUST NOT end up in Git

Per CLAUDE.md rule #12-13, the following are forbidden in committed files:

| Item | Where it lives |
|------|----------------|
| AWS access key / secret | GH Actions repository secrets (CI); `~/.aws/credentials` (operator) |
| Hosted zone ID (`Z0...`) | SSM `/sg-compute/vault-publish/bootstrap/zone-id` (resolved once at bootstrap, cached) |
| ACM cert ARN | SSM `/sg-compute/vault-publish/bootstrap/cert-arn` |
| CloudFront distribution ID | SSM `/sg-compute/vault-publish/bootstrap/cloudfront-distribution-id` |
| Lambda Function URL | SSM `/sg-compute/vault-publish/bootstrap/waker-function-url` |
| Vault keys (e.g. `sgit` dev-pack key) | Shared out-of-band (CLAUDE.md rule #13) |
| `sg-labs.app` registrar credentials | Operator's password manager — never the repo |

**SSM key paths simplified (decided 2026-05-17, flat scheme):** no `<namespace>` segment. Singular bootstrap.

The only `aws.sg-labs.app` reference legitimately allowed in Git is the **bare zone NAME** in documentation, examples, and `.env.example`-style template files (no ID, no ARN, no credentials).

### 4.4 Tension with CLAUDE.md AWS naming rules (#14, #15)

| Rule | Risk under aws.sg-labs.app scheme | Verdict |
|------|------------------------------------|---------|
| #14 — Security group `GroupName` must NOT start with `sg-` | The literal hostname segment `sg-labs` would trip the rule if used as an SG name. Vault-publish/lab work does not create SGs named after the zone (SGs are EC2-substrate-owned at `Vault_App__AWS__Client` and use names like `playwright-ec2`). **No risk.** Flagged so Dev does not invent an `sg-labs-*` SG name in passing. |
| #15 — AWS Name tag, never double-prefix | The Name tag for a vault-publish-owned EC2 is the **slug** (`sara-cv`), not the FQDN. No double-prefix risk. Confirm Dev does not concatenate `aws-sg-labs-sara-cv` into a tag. |

**Action:** add inline comments in `Vault_Publish__Service.register` (phase 1b) calling out rules #14 / #15 so Dev doesn't trip them when naming downstream resources.

---

## 5. Reuse map addendum

Same `REUSE / EXTEND / NEW` vocabulary as `02__reuse-map.md`.

| Concept | Existing artefact | Action |
|---------|-------------------|--------|
| Resolve `aws.sg-labs.app` hosted zone by name | `Route53__AWS__Client.find_hosted_zone_by_name` (`Route53__AWS__Client.py:76-82`) | REUSE |
| Lazy default-zone resolver from env var | `Route53__AWS__Client.default_zone_name()` (`Route53__AWS__Client.py:38-39`) + `resolve_default_zone()` (line 84-92) | REUSE |
| Upsert per-slug A record | `Route53__AWS__Client.upsert_record` (line 199-203) — via `Vault_App__Auto_DNS.run` | REUSE |
| Delete per-slug A record on stop / unpublish | `Route53__AWS__Client.delete_record` (line 205-214) | REUSE |
| Upsert wildcard ALIAS A under `aws.sg-labs.app` (CloudFront → A alias) | `Route53__AWS__Client.upsert_a_alias_record` (line 216-221) | REUSE |
| Resolve a FQDN's owning zone | `Route53__Zone__Resolver.resolve_zone_for_fqdn` (per `Vault_App__Auto_DNS.py:70`) | REUSE |
| Verify A record propagation post-mutation | `Route53__Authoritative__Checker.check` (per `Vault_App__Auto_DNS.py:90`) | REUSE |
| FQDN computation `slug.aws.sg-labs.app` | (no existing helper) | INLINE in `Vault_Publish__Service.register` — no separate `Fqdn__Builder` class (architect preference: inline; promote to a class only if a second caller appears) |
| `Reserved__Slugs` seed | `Reserved__Slugs` registry (NEW per `02 §5`) | EXTEND the planned NEW file with the hygiene seed list (Q15) |
| Singular bootstrap state in SSM | `osbot_aws.helpers.Parameter` (used by `Slug__Registry` per `02 §5`) | REUSE |
| Wildcard ACM cert provisioning | Already done — consume existing ARN | OUT OF SCOPE (cert pre-exists) |
| Orphan record cleanup | `sg aws dns records delete` CLI (`Cli__Dns.py:1022-1054`) | REUSE — operator-driven (Q12 defers a dedicated reaper) |

**No EXTEND of existing files** is required for the domain story beyond `Reserved__Slugs` seeding. No `namespace` field on `Schema__Vault_Publish__Bootstrap__Request`. No `Enum__Sg_Labs__Namespace`. No `Schema__Subdomain__Parts`.

---

## 6. Phase placement

Maps onto `04__phased-implementation.md`'s P0 → P2d structure. The domain work is **additive**, not a new phase.

| Phase | Domain-related deliverable | Scope |
|-------|----------------------------|-------|
| **P0** | ✅ COMPLETED 2026-05-17 — empirical verification on `sg-compute.sgraph.ai`. `aws.sg-labs.app` zone confirmed live with cert. | None remaining. |
| **P1a** (vault-app stop/start) | When `stop_stack` deletes the per-slug A record, target zone is **whatever `SG_AWS__DNS__DEFAULT_ZONE` resolves to**. With env unset, falls back to `sg-compute.sgraph.ai` (existing behaviour). With env set to `aws.sg-labs.app`, deletes from there. Tests run both. **Also: fix `delete_stack` to delete the per-slug A record (Q13).** | EXTEND P1a test matrix with one zone-name parametrise. |
| **P1b** (scaffold `vault_publish/`) | `Vault_Publish__Service.register` computes `f'{slug}.aws.sg-labs.app'` (or `f'{slug}.{zone_apex}'` from env). `Schema__Vault_Publish__Register__Request` has **no** `namespace` field. `Reserved__Slugs` seeded with the hygiene list (Q15). | No extra files. |
| **P2c** (Waker) | `Slug__From_Host` strips `.aws.sg-labs.app` from the `Host:` header and returns a `Safe_Str__Slug` directly. **No `Schema__Subdomain__Parts`.** | One less file than the old plan. |
| **P2d** (bootstrap) | `Schema__Vault_Publish__Bootstrap__Request` takes `--zone aws.sg-labs.app` and `--cert-arn <existing ARN>`. **No `namespace` field.** Singular SSM key paths (`/sg-compute/vault-publish/bootstrap/{cloudfront-distribution-id, lambda-name, zone, cert-arn, waker-function-url}`). Bootstrap is run once per environment. | Simpler schema + simpler SSM layout vs the old per-namespace plan. |

### 6.1 No new phase needed

Every domain deliverable folds into existing phase scope. The plan's serial-path estimate of ~12 working days (per `04__phased-implementation.md` cross-phase dependencies) is unchanged.

### 6.2 Where Dev should look first

Dev opens `08__decisions-applied.md` for the resolved-decision index, then `04__phased-implementation.md` for the phase-by-phase work. The phase tables in `04` stay the source of truth — `07` adds rows (now smaller after the flat-scheme decision), doesn't rewrite the phasing.

---

## 7. Open questions — historical record

The Q12 / Q13 / Q14 / Q15 / Q16 entries originally lived here. They are now consolidated into `06__open-questions.md` with their RESOLVED banners. See that file for the answer record. A new Q17 (lab-zone provisioning) is also captured there.

---

## 8. Summary — what changed compared to the pre-decision plan

1. **Default zone for vault-publish work shifts from `sg-compute.sgraph.ai` to `aws.sg-labs.app`** — by env var, not code. The constant in `Route53__AWS__Client.py:35` stays put.
2. **Subdomain scheme is FLAT** (`<slug>.aws.sg-labs.app`), not two-level. **Deletes** `Enum__Sg_Labs__Namespace` and `Schema__Subdomain__Parts` from the plan.
3. **One existing wildcard cert** (`*.aws.sg-labs.app`, ARN `arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa`, Issued) in `us-east-1` for CloudFront. **No cert work for v2.**
4. **Bootstrap is singular**, not per-namespace. SSM key prefix has no `<namespace>` segment.
5. **Reserved slugs** carry only the hygiene shadow list — no namespace tokens.
6. **Existing DNS / Route53 / Auto_DNS classes all REUSE unchanged.** Zero new boto3 surface. Zero change to `Route53__AWS__Client` or `Vault_App__Auto_DNS`.
7. **No new phase.** Folds into P1a / P1b / P2c / P2d. Smaller scope than the old per-namespace plan.
8. **All gating questions resolved.** See `08__decisions-applied.md` for the full index.
