---
title: "07 — Domain strategy: sg-labs.app for vault-publish and lab experiments"
file: 07__domain-strategy.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
status: PLAN — no code, no commits. Domain addendum to the vault-publish v2 plan.
---

# 07 — Domain strategy

The user has just registered `sg-labs.app` and created a Route 53 hosted zone for it. This file is the architectural addendum the previous six files were missing: it pins down the subdomain naming scheme, the cert strategy, the record lifecycle, and the hosted-zone wiring.

The plan deliberately keeps the **existing** `sg-compute.sgraph.ai` zone untouched for the vault-publish substrate (`sg vault-app` per `Route53__AWS__Client.DEFAULT_ZONE_NAME_FALLBACK` at `sgraph_ai_service_playwright__cli/aws/dns/service/Route53__AWS__Client.py:35`). `sg-labs.app` is **additive** — it becomes the canonical zone for everything that is *experimental* or *short-lived* (lab harness runs, throwaway demos, the v2 vault-publish work itself if the operator wants a clean break from `sg-compute.sgraph.ai`).

The single most important consequence: the existing `default_zone_name()` resolver (`Route53__AWS__Client.py:38-39`) reads `SG_AWS__DNS__DEFAULT_ZONE`. The vault-publish + lab work can switch zones by env var alone — zero code changes to the DNS layer.

---

## 1. Subdomain naming scheme

### 1.1 Options considered

| # | Scheme | Example | Verdict |
|---|--------|---------|---------|
| A | `<slug>.sg-labs.app` (flat) | `sara-cv.sg-labs.app` | Simple. Collides between v2 vault-publish slugs and lab experiments. |
| B | `<experiment>.sg-labs.app` (flat, lab-only) | `e10-zone-inventory.sg-labs.app` | Loses the slug abstraction. Doesn't suit vault-publish. |
| C | `<slug>.<lab>.sg-labs.app` (two-level) | `sara-cv.vp.sg-labs.app`, `e10.lab.sg-labs.app` | Clean separation. Wildcard cert needs care. |
| D | `<env>.<slug>.sg-labs.app` | `prod.sara-cv.sg-labs.app` | Premature — no env story yet. |
| E | **Hybrid: `<slug>.<namespace>.sg-labs.app` with reserved namespaces `vp` (vault-publish) and `lab` (lab harness)** | `sara-cv.vp.sg-labs.app`, `e10-zone-inventory.lab.sg-labs.app` | **Recommended.** |

### 1.2 Recommended scheme (E)

**Production form:** `<slug>.<namespace>.sg-labs.app`

Where:

- `<slug>` is the existing `Safe_Str__Slug` primitive (regex `[a-z0-9\-]+`, max 40, charset enforced at construction — see `03__delta-from-lab-brief.md §A.7` and reuse-map row "Safe_Str__Slug").
- `<namespace>` is a **closed enum** of registered apps. Initial members:
  - `vp` — vault-publish (`sg vault-publish register sara-cv` → `sara-cv.vp.sg-labs.app`)
  - `lab` — lab harness experiments (`sg aws lab run e10` → `e10.lab.sg-labs.app`)
- The apex `sg-labs.app` and bare-second-level names (e.g. `vp.sg-labs.app` with no slug prefix) are **reserved for platform control-plane records** (CloudFront wildcard, ACM DNS-validation records, future status pages).

Worked examples:

| Operator command | Resulting FQDN |
|------------------|----------------|
| `sg vp register sara-cv` | `sara-cv.vp.sg-labs.app` |
| `sg vp register hello-world` | `hello-world.vp.sg-labs.app` |
| Lab E10 zone-inventory run | `e10-zone-inventory.lab.sg-labs.app` (if the experiment chooses to publish) |
| Lab E27 registry-load demo (if `Slug__Registry` backs it per `06__open-questions.md` Q1) | `e27-load.lab.sg-labs.app` |

### 1.3 Rationale

1. **No collisions.** A lab experiment named `sara-cv` cannot accidentally claim the same FQDN as a registered vault-publish slug — the namespace separates them.
2. **One wildcard cert per namespace** (see §2) — much cheaper to provision and rotate than per-FQDN certs.
3. **Operator-readable.** `*.vp.sg-labs.app` reads as "vault-publish app". `*.lab.sg-labs.app` reads as "lab experiment". The CLI namespace and the DNS namespace are the same string.
4. **No conflict with existing primitives.** `Safe_Str__Slug` continues to validate just the leaf; the namespace lives in a separate enum.
5. **Forward-compatible with multi-env.** When (eventually) needed, `<env>.<slug>.<namespace>.sg-labs.app` (option D, three-level) extends naturally — no rename of existing records.

### 1.4 Reconciliation with existing plan primitives

| Existing primitive | How it fits scheme E |
|--------------------|----------------------|
| `Safe_Str__Slug` (per `02__reuse-map.md §5`) | Still validates the **leaf** only. Unchanged. |
| `Slug__Validator` (reserved list + policy) | Unchanged — runs against the leaf. **Add** namespace strings to `Reserved__Slugs` so nobody registers `lab` or `vp` as a vault-publish slug (would create a record that shadows the namespace's parent label). |
| `Schema__Vault_Publish__Register__Request.fqdn` | Computed as `f'{slug}.vp.{zone_apex}'` rather than `f'{slug}.{zone_apex}'`. One-line change in the orchestrator (`Vault_Publish__Service.register`). |
| `Route53__Zone__Resolver.resolve_zone_for_fqdn` | Already walks labels right-to-left; finds `sg-labs.app` zone for any FQDN under it regardless of depth. No change. Verified — `Vault_App__Auto_DNS.run` (`sg_compute_specs/vault_app/service/Vault_App__Auto_DNS.py:70`) uses it. |
| `Slug__From_Host` (Waker — phase 2c) | Parses `Host:` header. Must strip the namespace label first: `sara-cv.vp.sg-labs.app` → slug=`sara-cv`, namespace=`vp`. **Add a `Schema__Subdomain__Parts` return type** rather than a tuple (per `03__delta-from-lab-brief.md §A.8`). |
| `DEFAULT_ZONE_NAME_FALLBACK` constant | Stays at `sg-compute.sgraph.ai` for `sg vault-app`. Vault-publish + lab work overrides via `SG_AWS__DNS__DEFAULT_ZONE=sg-labs.app`. **Do NOT change the constant** — it's the substrate's default. |

### 1.5 The `Enum__Sg_Labs__Namespace` class

New file, owned by `sg_compute_specs/vault_publish/` (since it's where the namespace concept first becomes operational). One file per class per CLAUDE.md rule #21.

```
sg_compute_specs/vault_publish/schemas/Enum__Sg_Labs__Namespace.py
```

```python
# Enum__Sg_Labs__Namespace.py
class Enum__Sg_Labs__Namespace(Enum):
    VP  = 'vp'      # vault-publish — operator-published vault apps
    LAB = 'lab'     # lab harness experiments
    # Add new members one PR at a time. Each addition needs:
    #   1. a Reserved__Slugs entry so nobody registers it as a leaf,
    #   2. a Route 53 ALIAS / wildcard A record under the namespace label
    #      (created by the namespace's owning spec's `bootstrap`),
    #   3. an ACM cert (wildcard for the namespace — see §2).
```

The lab spec (if/when it lands per `06__open-questions.md` Q1) imports the same enum. The enum lives under `vault_publish/` because vault-publish ships first; if a future shared package emerges, it migrates there with a re-export shim.

---

## 2. Certificate strategy

### 2.1 Options considered

| # | Scheme | Coverage | Verdict |
|---|--------|----------|---------|
| A | One wildcard per apex: `*.sg-labs.app` | Covers `sara-cv.sg-labs.app` but **NOT** `sara-cv.vp.sg-labs.app` (wildcards are single-label per RFC 6125). | Insufficient for scheme E. |
| B | One wildcard per namespace: `*.vp.sg-labs.app`, `*.lab.sg-labs.app` | Covers all scheme-E leaves. Two certs total today, one per added namespace later. | **Recommended.** |
| C | Per-FQDN ACM cert, issued on `vp register` | Most precise; LE-style. Adds ~3 min latency per register and a DNS-01 challenge dance. Hits ACM service quotas at scale (default 2000 certs / region / year). | Over-engineered for v2. |
| D | One SAN cert covering `*.vp.sg-labs.app`, `*.lab.sg-labs.app`, `*.sg-labs.app` | Single ARN to manage. But every namespace addition requires re-validation of all SANs. | Reject — operationally fragile. |

### 2.2 Recommended (B): one wildcard ACM cert per namespace

**Initial provisioning (manual, one-time):**

```
# Operator, once per environment, in us-east-1 (CloudFront requirement):
aws acm request-certificate \
    --domain-name '*.vp.sg-labs.app' \
    --validation-method DNS \
    --region us-east-1
# (repeat for *.lab.sg-labs.app when the lab spec lands)
```

DNS-01 validation records get written into the `sg-labs.app` zone (via `sg aws dns records add` — existing surface, gated by `SG_AWS__DNS__ALLOW_MUTATIONS=1` per `Cli__Dns.py:117-119`).

**Operator passes the ARN to `bootstrap`:**

```bash
sg vp bootstrap --zone sg-labs.app \
                --namespace vp \
                --cert-arn arn:aws:acm:us-east-1:...:certificate/<id>
```

The cert ARN gets stored in SSM at `/sg-compute/vault-publish/bootstrap/<namespace>/cert-arn` (matches `06__open-questions.md` Q10's SSM-only decision). One CloudFront distribution per namespace consumes that ARN.

### 2.3 Region implications

- **CloudFront requires `us-east-1` ACM certs.** Both wildcards live in `us-east-1` regardless of the Waker Lambda's region (which is `eu-west-2` per the brief's defaults).
- **The Waker Lambda's Function URL is in the Waker's region.** Function URLs auto-issue an AWS-managed TLS cert on `*.lambda-url.<region>.on.aws`. Operator-facing certs (the wildcards) only sit in front of CloudFront. The path is `client → CloudFront (us-east-1 cert) → Function URL (region-managed cert) → EC2 origin (per-FQDN LE cert via existing cert-init container)`.
- **ALB / API Gateway aren't in scope.** The brief uses Lambda Function URLs as the Waker origin (`04__phased-implementation.md` Phase 2b). If a later brief swaps to API Gateway, the cert strategy is unchanged (Regional API Gateway also wants a regional ACM cert for custom domains, but for the wildcard-on-CloudFront edge cert nothing changes).

### 2.4 What about the EC2-direct cert post-warm?

When the Waker drops out of the path (DNS swap from wildcard ALIAS-to-CloudFront to specific-A-to-EC2 IP — brief [`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) step 7), the browser hits the EC2 directly. The EC2 needs its own cert for `<slug>.vp.sg-labs.app` — this is **already** handled by the existing `cert-init` container with Let's Encrypt issuance (substrate confirmed by `01__grounding.md §1.4` user-data builder).

The wildcard ACM cert and the per-FQDN LE cert co-exist:

- Wildcard ACM cert → CloudFront edge → cold path.
- Per-FQDN LE cert → EC2 nginx → warm path.

Both serve traffic for the same FQDN, at different times in the slug's lifecycle. Neither blocks the other.

### 2.5 Trade-offs of (B)

- **Operational footprint:** small — two certs (vp, lab), each auto-renewed by ACM forever.
- **Adding a namespace:** new wildcard cert, ~5 min wall-clock (DNS validation). One PR adds the namespace enum member, one operator command provisions the cert, one bootstrap command wires it in.
- **Compromise blast radius:** if the `*.vp.sg-labs.app` private key leaks (highly unlikely — ACM keys are not exportable), only vp namespace traffic is at risk. Lab is unaffected.
- **No coupling to specific slugs:** an operator can register / unpublish slugs all day without touching ACM.

---

## 3. Route 53 record lifecycle

### 3.1 Inventory of record types per slug

For a fully-warm vault-publish slug `sara-cv` under namespace `vp`:

| Record | Type | TTL | Lifecycle | Owner |
|--------|------|-----|-----------|-------|
| `*.vp.sg-labs.app` | A ALIAS → CloudFront | n/a (alias) | Created at bootstrap. **Never deleted** during normal operation. | `Vault_Publish__Service.bootstrap` (phase 2d) |
| `sara-cv.vp.sg-labs.app` | A | 60 s | Created on `register` (after EC2 boot) **OR** on `start` (after stop→start). Deleted on `unpublish` **OR** on `stop`. | `Vault_App__Auto_DNS.run` (existing); deletion = new `delete_per_slug_a_record` helper in phase 1a |
| ACM DNS-01 validation | CNAME | ACM-managed | Created at cert-issuance time. Lives forever (ACM uses it for renewal). | Operator, once |

### 3.2 Who creates, who deletes

| Action | Reads | Writes | Service class |
|--------|-------|--------|---------------|
| `sg vp bootstrap` (phase 2d) | — | wildcard ALIAS A under namespace label | `Vault_Publish__Service.bootstrap` → `Route53__AWS__Client.upsert_a_alias_record` (`Route53__AWS__Client.py:216-221` — already exists, REUSE) |
| `sg vp register <slug>` (phase 1b) | wildcard ALIAS for verification | per-slug A record (after `vault-app create_stack` returns the IP) | `Vault_Publish__Service.register` → existing `Vault_App__Service.create_stack` (which internally calls `Vault_App__Auto_DNS.run`) |
| `sg vault-app stop <slug>` (phase 1a) | — | **deletes** the per-slug A record. **Does not** touch the wildcard. | `Vault_App__Service.stop_stack` → new `delete_per_slug_a_record` → `Route53__AWS__Client.delete_record` (`Route53__AWS__Client.py:205-214` — REUSE) |
| `sg vault-app start <slug>` (phase 1a) | — | **re-creates** the per-slug A record with the new public IP | `Vault_App__Service.start_stack` → reuses `Vault_App__Auto_DNS.run` (same code path as `create_stack`) |
| `sg vp unpublish <slug>` (phase 1b) | — | **deletes** per-slug A; **deletes** SSM registry entry; calls `vault_app.delete_stack` | `Vault_Publish__Service.unpublish` → composes the two existing services |
| Stack teardown by other means (e.g. ops kills the EC2 by hand) | — | **does not** delete the per-slug A record | — — see §3.4 (reaper) |

### 3.3 TTL policy

- **Per-slug A records: 60 s.** Matches `Vault_App__Auto_DNS.AUTO_DNS__RECORD_TTL_SEC` (`Vault_App__Auto_DNS.py:27`). Short TTL is load-bearing — the Waker's "DNS swap after warm" relies on browsers picking up the specific A record within one TTL window. Do not raise.
- **Wildcard ALIAS: ACM/CF-managed.** Alias records have no caller-configurable TTL; CloudFront's edge cache rules apply.
- **ACM validation CNAMEs: ACM-managed.** Operator does not touch.

### 3.4 Stale-record reaper

**PROPOSED — does not exist yet.** Out of v2 scope; mentioned here to make the gap explicit so it doesn't become a bad failure (CLAUDE.md rule #27).

Scenarios that leave stale per-slug A records:

1. EC2 instance terminated outside `sg vault-app delete` (e.g. operator panic, AWS console).
2. `vault-app stop` succeeded but the DNS-delete network call failed (the brief's design captures this in `Schema__Vault_App__Stop__Response.dns_record_deleted=False` — see `03__delta-from-lab-brief.md §A.1`).
3. `Slug__Registry` SSM entry deleted manually but the A record wasn't.

**Recommended follow-up (phase-2d-followup):**

A `sg vp reap` verb that:

1. Lists every per-slug A record under `*.vp.sg-labs.app` (via `Route53__AWS__Client.list_records` — already exists, REUSE).
2. Cross-references against `Slug__Registry.list_slugs()` and EC2 tag scan (`StackType=vault-app`).
3. Reports orphans; deletes on `--apply`. Gated by `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1`.

Added to `06__open-questions.md` as **Q12** (non-blocking; deferrable).

### 3.5 Stack teardown contract

When `sg vault-app delete <slug>` is invoked, the per-slug A record gets deleted as part of `delete_stack`. **This must be true today** — verify in phase 1a's regression test pass. If it's not (the existing `Vault_App__Service.delete_stack` at line 528 may not delete DNS — needs an audit Dev does in phase 1a), this becomes a bad failure of the substrate and must be fixed before vault-publish ships.

Added to `06__open-questions.md` as **Q13** (gating for phase 1a Dev work — must verify).

---

## 4. Hosted-zone wiring

### 4.1 Where the zone ID lives

**Recommendation: env var + late-binding resolver, NEVER in Git.**

Pattern, mirroring `Route53__AWS__Client.default_zone_name()` (line 38-39):

```python
# sgraph_ai_service_playwright__cli/aws/dns/service/Route53__AWS__Client.py — EXISTING
SG_AWS__DNS__DEFAULT_ZONE   = 'sg-labs.app'             # operator sets this
SG_AWS__DNS__DEFAULT_ZONE_ID = 'Z0123456789ABCDEFGHIJ'  # optional override; auto-resolved by name otherwise
```

The **zone NAME** lives in env (`SG_AWS__DNS__DEFAULT_ZONE`). The **zone ID** is resolved lazily by name lookup (`find_hosted_zone_by_name` at `Route53__AWS__Client.py:76-82` — exists, no change). The operator never types a zone ID.

**Why not a config schema field?**

- A `Schema__Vault_Publish__Bootstrap__Request.zone` field is fine — the CLI accepts `--zone sg-labs.app` and writes the bootstrap context to SSM. **The zone ID is never persisted in code.**
- The auto-discover-by-name pattern is already proven in `Vault_App__Auto_DNS.run` (line 70: `zone = self._zone_resolver(client).resolve_zone_for_fqdn(fqdn)`).

### 4.2 Cross-account considerations

**Out of scope for v2.** Single-account assumption (everything in the operator's default AWS account). If multi-account ever lands, the resolver picks up an STS-assumed-role boto3 session; no schema change.

Added to `06__open-questions.md` as **Q14** for future thinking.

### 4.3 What MUST NOT end up in Git

Per CLAUDE.md rule #12-13, the following are forbidden in committed files:

| Item | Where it lives |
|------|----------------|
| AWS access key / secret | GH Actions repository secrets (CI); `~/.aws/credentials` (operator) |
| Hosted zone ID (`Z0...`) | SSM `/sg-compute/vault-publish/bootstrap/<namespace>/zone-id` (resolved once at bootstrap, cached) |
| ACM cert ARN | SSM `/sg-compute/vault-publish/bootstrap/<namespace>/cert-arn` |
| CloudFront distribution ID | SSM `/sg-compute/vault-publish/bootstrap/<namespace>/cloudfront-distribution-id` |
| Lambda Function URL | SSM `/sg-compute/vault-publish/bootstrap/<namespace>/waker-function-url` |
| Vault keys (e.g. `sgit` dev-pack key) | Shared out-of-band (CLAUDE.md rule #13) |
| `sg-labs.app` registrar credentials | Operator's password manager — never the repo |

The only `sg-labs.app` reference legitimately allowed in Git is the **bare zone NAME** in documentation, examples, and `.env.example`-style template files (no ID, no ARN, no credentials).

**Tension check.** None of the user's choices conflict with CLAUDE.md rules — zone names are not secrets, and the env-var + SSM pattern avoids committing IDs.

### 4.4 Tension with CLAUDE.md AWS naming rules (#14, #15)

| Rule | Risk under sg-labs.app scheme | Verdict |
|------|-------------------------------|---------|
| #14 — Security group `GroupName` must NOT start with `sg-` | The literal hostname segment `sg-labs` would trip the rule if used as a Security-Group name. The vault-publish/lab work does not create SGs named after the zone (SGs are EC2-substrate-owned at `Vault_App__AWS__Client` and use names like `playwright-ec2`). **No risk.** Flagged so Dev does not invent an `sg-labs-*` SG name in passing. |
| #15 — AWS Name tag, never double-prefix | The Name tag for a vault-publish-owned EC2 is the **slug** (`sara-cv`), not the FQDN. No double-prefix risk. Confirm Dev does not concatenate `sg-labs-sara-cv` into a tag. |

**Action:** add inline comments in `Vault_Publish__Service.register` (phase 1b) calling out rules #14 / #15 so Dev doesn't trip them when naming downstream resources.

---

## 5. Reuse map addendum

Same `REUSE / EXTEND / NEW` vocabulary as `02__reuse-map.md`.

| Concept | Existing artefact | Action |
|---------|-------------------|--------|
| Resolve `sg-labs.app` hosted zone by name | `Route53__AWS__Client.find_hosted_zone_by_name` (`Route53__AWS__Client.py:76-82`) | REUSE |
| Lazy default-zone resolver from env var | `Route53__AWS__Client.default_zone_name()` (`Route53__AWS__Client.py:38-39`) + `resolve_default_zone()` (line 84-92) | REUSE |
| Upsert per-slug A record | `Route53__AWS__Client.upsert_record` (line 199-203) — via `Vault_App__Auto_DNS.run` | REUSE |
| Delete per-slug A record on stop / unpublish | `Route53__AWS__Client.delete_record` (line 205-214) | REUSE |
| Upsert wildcard ALIAS A under namespace (CloudFront → A alias) | `Route53__AWS__Client.upsert_a_alias_record` (line 216-221) | REUSE |
| Resolve a FQDN's owning zone (handles multi-label depth) | `Route53__Zone__Resolver.resolve_zone_for_fqdn` (per `Vault_App__Auto_DNS.py:70`) | REUSE |
| Verify A record propagation post-mutation | `Route53__Authoritative__Checker.check` (per `Vault_App__Auto_DNS.py:90`) | REUSE |
| `Enum__Sg_Labs__Namespace` (vp, lab, …) | (no existing) | NEW — `sg_compute_specs/vault_publish/schemas/Enum__Sg_Labs__Namespace.py` (one file per CLAUDE.md rule #21) |
| `Schema__Subdomain__Parts` (slug + namespace + apex; returned by `Slug__From_Host`) | (no existing) | NEW — `sg_compute_specs/vault_publish/waker/schemas/Schema__Subdomain__Parts.py` (replaces tuple — see `03 §A.8`) |
| `Reserved__Slugs` to block namespace strings as leaves | `Reserved__Slugs` registry (NEW per `02 §5`) | EXTEND the planned NEW file to seed it with the namespace enum values |
| FQDN computation `slug.namespace.zone` | (no existing helper) | NEW — `sg_compute_specs/vault_publish/service/Fqdn__Builder.py` or inline in `Vault_Publish__Service.register` (architect preference: inline for now; promote to a class if a second caller appears) |
| Per-namespace bootstrap state in SSM | `osbot_aws.helpers.Parameter` (used by `Slug__Registry` per `02 §5`) | REUSE |
| Wildcard ACM cert provisioning | (operator action — outside the spec; brief Q7 keeps cert issuance manual) | OUT OF SCOPE |

**No EXTEND of existing files** is required for the domain story beyond the `Reserved__Slugs` seeding and the per-namespace `bootstrap` argument additions to `Schema__Vault_Publish__Bootstrap__Request` (already a NEW file per `04__phased-implementation.md` Phase 2d).

---

## 6. Phase placement

Maps onto `04__phased-implementation.md`'s P0 → P2d structure. The domain work is **additive**, not a new phase — it adds requirements to existing phases.

| Phase | Domain-related deliverable | New / existing scope |
|-------|----------------------------|----------------------|
| **P0** (manual smoke test) | Operator confirms `sg-labs.app` zone is resolvable from the operator's AWS account: `aws route53 list-hosted-zones \| grep sg-labs.app`. Confirms `SG_AWS__DNS__DEFAULT_ZONE=sg-labs.app` resolves via `find_hosted_zone_by_name` (one-liner test). | NEW — append to P0 manual checklist. |
| **P1a** (vault-app stop/start) | When `stop_stack` deletes the per-slug A record, target zone is **whatever `SG_AWS__DNS__DEFAULT_ZONE` resolves to**. With env unset, falls back to `sg-compute.sgraph.ai` (existing behaviour, no change). With env set to `sg-labs.app`, deletes from there. Tests run both. | EXTEND P1a test matrix — one extra parametrise over zone-name. |
| **P1b** (scaffold `vault_publish/`) | `Enum__Sg_Labs__Namespace` ships. `Reserved__Slugs` seeded with namespace strings (`vp`, `lab`). `Vault_Publish__Service.register` computes `f'{slug}.vp.{zone_apex}'` for the FQDN. `Schema__Vault_Publish__Register__Request` carries a `namespace : Enum__Sg_Labs__Namespace = Enum__Sg_Labs__Namespace.VP` field (default vp; lab spec overrides). | NEW — adds ~2 files to P1b scope: `Enum__Sg_Labs__Namespace.py` + the namespace field in the register-request schema. |
| **P2c** (Waker) | `Slug__From_Host` returns `Schema__Subdomain__Parts(slug, namespace, apex)` rather than just a slug. The Waker can refuse requests for an unknown namespace (404 fast) before any AWS call. | NEW — adds ~1 file to P2c scope: `Schema__Subdomain__Parts.py`. Already implied by `03 §A.8`. |
| **P2d** (bootstrap) | `Schema__Vault_Publish__Bootstrap__Request` gets a required `namespace : Enum__Sg_Labs__Namespace` field. Per-namespace SSM key paths (`/sg-compute/vault-publish/bootstrap/<namespace>/...`). Bootstrap is run once per namespace per environment. | EXTEND P2d schema + SSM key layout — small change. |

### 6.1 No new phase needed

Every domain deliverable folds into existing phase scope. The plan's serial-path estimate of ~12 working days (per `04__phased-implementation.md` cross-phase dependencies) does **not** materially change; add ~0.5 day across P1b and P2d combined.

### 6.2 Where Dev should look first

Dev opens `04__phased-implementation.md` and treats this section as a checklist amendment to the phase tables there. The phase tables in `04` stay the source of truth — `07` adds rows, doesn't rewrite the phasing.

---

## 7. Open questions (continuing from `06__open-questions.md`)

Numbered Q12 onward to extend the existing list.

### Q12 — Build the stale-record reaper now or later?

**Context:** §3.4 above. Out of v2 scope today.

**Options:**

| Opt | Position |
|-----|----------|
| A | Defer. Add `Q12` to a phase-2d-followup list; ship v2 without it. |
| B | Inline into P2d. Adds ~0.5 day. |

**Architect's recommendation:** **A** — defer. The reaper is a hygiene tool, not a feature; the operator can `sg aws dns records list` and clean up manually in the v2 window.

**Gating:** non-gating. Adds a follow-up entry to `library/roadmap/`.

### Q13 — Does `Vault_App__Service.delete_stack` already delete the per-slug A record?

**Context:** §3.5 above. Today's `delete_stack` at `Vault_App__Service.py:528` needs an audit before Dev finalises P1a's `stop_stack` design. If it does NOT delete the DNS record, every stack ever terminated by `sg vault-app delete` has been leaking an A record into `sg-compute.sgraph.ai`.

**Action:** Dev to grep `Vault_App__Service.delete_stack` for any call to `Route53__AWS__Client.delete_record` or `Vault_App__Auto_DNS` cleanup. If absent: file a substrate-bug debrief (CLAUDE.md rule #27 — bad failure), fix in P1a, add a reaper run as a one-shot cleanup.

**Architect's recommendation:** Dev runs the audit at the very start of P1a; no human decision needed beyond "did the audit happen".

**Gating:** **gating for P1a.** The stop/start design assumes `delete_stack` is the reference DNS-delete path; if it's broken, the design needs to fix it first.

### Q14 — Cross-account hosted zones?

**Context:** §4.2. Multi-account is out of v2 scope.

**Architect's recommendation:** defer. Park in `library/roadmap/`. Not a phase-2d concern.

**Gating:** non-gating.

### Q15 — Should `Slug__Validator` reject slugs that shadow the **second-level** label?

**Context:** §1.5 — `Reserved__Slugs` seeded with `vp` and `lab`. But what about `www`, `api`, `admin`, `status` — common DNS labels that may be needed at the namespace level later (e.g. `status.vp.sg-labs.app` for a vp-namespace status page)?

**Options:**

| Opt | Position |
|-----|----------|
| A | Seed `Reserved__Slugs` with a generous list now: `vp`, `lab`, `www`, `api`, `admin`, `status`, `mail`, `cdn`, `auth`. |
| B | Minimal seed (`vp`, `lab` only); add more as needs surface. |

**Architect's recommendation:** **A** — generous seed. Cheaper to allow a slug later (just remove from reserved list) than to migrate an unintentionally-claimed slug.

**Gating:** non-gating, but should be settled before P1b ships so the test data is right.

### Q16 — Does the lab spec ship with `*.lab.sg-labs.app` cert in v2's bootstrap, or wait for its own phase?

**Context:** Per `06__open-questions.md` Q1, the lab work is a sibling track. The `vp` wildcard cert is essential for v2; the `lab` wildcard cert is essential only when the lab spec ships.

**Architect's recommendation:** v2 phase 2d operator provisions **only** `*.vp.sg-labs.app`. The lab provisions its own `*.lab.sg-labs.app` cert when that spec lands. Bootstrap is per-namespace, so the two cert issuances are independent.

**Gating:** non-gating (lab is sibling track).

---

## 8. Summary — what changes compared to the pre-`sg-labs.app` plan

1. **Default zone for vault-publish work shifts from `sg-compute.sgraph.ai` to `sg-labs.app`** — by env var, not code. The constant in `Route53__AWS__Client.py:35` stays put.
2. **Subdomain scheme is now two-level under a namespace label** (`<slug>.vp.sg-labs.app`), not flat. Adds an `Enum__Sg_Labs__Namespace` and a `Schema__Subdomain__Parts` (replaces tuple).
3. **Cert strategy is one wildcard per namespace**, both in `us-east-1` for CloudFront.
4. **Bootstrap is per-namespace.** SSM key prefix gains a `<namespace>` segment.
5. **Reserved slugs gain the namespace strings + a generous shadow list** (Q15 pending).
6. **Existing DNS / Route53 / Auto_DNS classes all REUSE unchanged.** Zero new boto3 surface. Zero change to `Route53__AWS__Client` or `Vault_App__Auto_DNS`.
7. **No new phase.** Folds into P0 / P1a / P1b / P2c / P2d. Adds ~0.5 dev-day end-to-end.
8. **Five new open questions (Q12–Q16).** One gating (Q13 — substrate audit of `delete_stack`).
