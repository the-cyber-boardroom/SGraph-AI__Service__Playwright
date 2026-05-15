---
title: "Architect Briefing — vault-app: CloudFront + Route 53 + ACM"
file: architect__vault-app__cf-route53__plan.md
author: Architect (Claude)
date: 2026-05-15 (UTC hour 03)
repo: SGraph-AI__Service__Playwright @ dev (v0.1.140 line, vault-app v0.2.6)
status: PLAN — no code, no commits. For human ratification before Dev picks up.
parent:
  - team/roles/architect/reviews/05/14/v0.2.6__vault-app-tls-options.md
  - team/roles/architect/reviews/05/14/v0.2.6__vault-app-tls-poc-fastapi-sidecar.md
---

# Architect Briefing — vault-app: CloudFront + Route 53 + ACM

> **PROPOSED — does not exist yet.** Nothing in this brief is implemented today.
> CloudFront, Route 53, and ACM helpers are absent from `sg_compute*` (verified:
> no `route53` / `cloudfront` / `acm` references outside this brief's lineage).
> The TLS lineage this builds on *is* shipped — see §1.

---

## 1. Context & current state

Where vault-app stands today (code-verified against `dev` HEAD `0fd84f3`):

- **Reality doc:** master index at `team/roles/librarian/reality/index.md` records repo
  version **v0.1.140**; the vault-app spec ships under `sg_compute_specs/vault_app/`.
  The vault domain is still seeded from recent commits (no migrated `vault/index.md`
  yet — see migration shim table). This brief is therefore PROPOSED until a Dev slice
  lands and a reality entry is written.
- **TLS lineage (shipped):**
  - `27d5647` — TLS P0 PoC: `sg_compute/platforms/tls/` library (Cert__Generator /
    Cert__Inspector / cert_init), `Fast_API__TLS__Launcher` (§8.2 contract:
    `FAST_API__TLS__{ENABLED,CERT_FILE,KEY_FILE,PORT}`), slim `Fast_API__TLS` app.
  - `8aad135` — Let's Encrypt IP cert wired into the vault EC2 path via
    `Cert__ACME__Client` + `ACME__Challenge__Server`; cert-init dispatches on
    `SG__CERT_INIT__MODE` (`self-signed` | `letsencrypt-ip`); `--acme-prod` for
    production directory; `:443` and `:80` world-open for http-01 when TLS on.
  - `9626e52` — TLS production by default: `with_tls_check=True`,
    `tls_mode='letsencrypt-ip'`, `acme_prod=True`. `vault_url` becomes
    `https://<public_ip>` (no port; 443 implicit). New tags `StackTLS`,
    `AccessToken` surfaced via `Vault_App__Stack__Mapper.to_info`.
- **Architect lineage (design):**
  - `e4b55c6` — research doc, five options (A Caddy / B1 LE-IP / B2 DNS / C in-app /
    D ALB+CF / E port-forward).
  - `012adb0` — design doc, FastAPI TLS sidecar PoC, phases P0..P3.
  - `d44863a` — **Q6 resolved:** in-app uvicorn TLS, no proxy anywhere. Caddy and
    all reverse-proxy paths superseded out of the design. CloudFront/ALB
    (Option D) was rejected in `e4b55c6` for ephemeral stacks; **this brief
    revisits CloudFront under different framing**: not as the TLS data plane, but
    as a DNS-fronted edge (Q4 / Option B2 in the research doc was the deferred
    "DNS + hostname certs" path — this is that brief).

What `vault_url` looks like today (`Vault_App__Stack__Mapper.py:48-51`):

```
public_ip → https://<public_ip>   (TLS on)  or  http://<public_ip>:8080  (plain)
```

Reachability: caller `/32` for the upstream port plus `:443` + `:80` world-open during
ACME issuance (`Vault_App__Service.py:88-99`). Access token surfaced two ways: the
`AccessToken` EC2 tag (ec2:DescribeInstances) and the existing in-band auth (`X-API-Key`
header / `x-sgraph-access-token` cookie / `?access_token=` query for the auth form).

What is **not** in the repo today (verified with grep):

- No Route 53 / hosted-zone / CNAME / Alias-record code anywhere in `sg_compute*`.
- No ACM helpers, no DNS-validation code.
- No CloudFront distribution code.
- No osbot-aws import for any of the above (only `EC2`, `IAM_Role`, `Parameter`,
  `AWS_Config`, `Create_Image_ECR` are imported across the repo).

This brief therefore proposes a **net-new shared platform module** alongside
`sg_compute/platforms/tls/` and `sg_compute/platforms/ec2/`: a new
`sg_compute/platforms/dns/` (Route 53) and `sg_compute/platforms/edge/` (CloudFront +
ACM). The vault-app spec is the first consumer; other specs adopt later.

---

## 2. Goals & non-goals

### Goals

1. **Browser-trusted HTTPS via a stable hostname** for a vault-app stack —
   `https://<stack>.vault.sgraph.ai` instead of `https://<public-ip>`.
2. **Eliminate the LE-IP renewal cliff** for stacks that outlive ~160 h: a Route 53
   record + a long-lived ACM-managed cert (90-day, auto-renewed) at the edge,
   instead of a `shortlived` IP cert with ~6.7-day validity.
3. **Hide the EC2 origin IP** from clients; only CloudFront IPs face the public
   internet. The vault-app SG can tighten to "CloudFront origin only" instead of
   "world-open during ACME + caller /32 thereafter".
4. **Preserve `one image / five targets`** — Lambda/CI/laptop/Claude-Web/Fargate
   unaffected. CloudFront is *deployment composition*, not an image change.
5. **Preserve the §8.2 TLS launch contract** — in-app uvicorn TLS still works for
   stacks that opt out of CloudFront. CF mode is additive.
6. **`osbot-aws` discipline** — no direct boto3 except documented narrow exceptions,
   following the existing `Vault_App__AWS__Client` boundary pattern.

### Non-goals

- Replacing the LE-IP path. P0/P1 in this brief keep LE-IP as the default; CF is opt-in.
- A WAF layer. CloudFront makes WAF possible; this brief flags it as a follow-up,
  does not deliver it.
- Multi-region / fail-over. Single region, single distribution per stack.
- Per-environment hosted zones. One zone per repo (e.g. `vault.sgraph.ai`); per-stack
  subdomain.
- A general CDN/caching strategy. The vault UI is dynamic + auth-gated; CF is used
  for TLS termination + a stable name, **not** for caching (see Q5).
- Touching the playwright service's 12-class layout, `Step__Executor`,
  `Artefact__Writer`, or the JS allowlist. This is pure infra.

---

## 3. Open questions — for human ratification before Dev starts

Style mirrors `d44863a` / Q6 in `v0.2.6__vault-app-tls-poc-fastapi-sidecar.md`: each
question lists A/B/C options and one Architect recommendation.

### Q1 — Why CloudFront at all?

| Opt | Position |
|-----|----------|
| **A** | **DNS + hostname cert only** — Route 53 alias → EIP (no CF). Use ACM-issued cert directly on the EC2 (DNS-01 via Route 53, public-trust). No CDN, no edge. |
| **B** | **CloudFront in front of EC2** — get hostname + ACM + origin IP hiding + WAF surface, accept ~15-min create/destroy and the cache-policy decisions it forces. |
| **C** | **ALB + ACM** — middle-ground (regional, faster than CF, supports WAF, real load balancing) but adds an ALB per ephemeral stack — slow, separately-billed, heavy. |

**Recommendation: B, but only when the user wants a *long-lived* vault.** CloudFront
earns its keep when (a) the stack is expected to live well beyond 6 days (the LE-IP
renewal horizon) or (b) the origin IP must be hidden. For ephemeral one-hour stacks,
**A (DNS-only)** is the better default — same hostname benefit, no 15-min CF dance.
Therefore the brief proposes **both modes** behind one spec flag:

- `--edge-mode none`         (default, today's behaviour: bare LE-IP)
- `--edge-mode dns-only`     (Route 53 A-record → EIP; ACM cert via DNS-01; in-app TLS)
- `--edge-mode cloudfront`   (full CF in front; ACM in us-east-1; CF→origin TLS)

Option C (ALB) is rejected for the same reason `e4b55c6` rejected it: per-stack ALB
provisioning is heavyweight and not warranted for our typical workload shape.

### Q2 — Origin TLS posture when CloudFront is in front?

| Opt | Position |
|-----|----------|
| **A** | **HTTPS origin with the existing LE-IP cert** — CF→origin over `https://<eip>`, viewer-to-CF over `https://<host>` with ACM cert. Two certs in play. |
| **B** | **HTTPS origin with a self-signed cert** + CF `OriginSSLProtocols=TLSv1.2` and `OriginProtocolPolicy=https-only`. CF *trusts* the origin (it can't validate the chain anyway — CF only validates publicly-trusted ones) — wait, this is wrong: CF *does* require a publicly-trusted origin cert when origin is HTTPS. Strike B. |
| **B'** | **HTTPS origin with the LE-IP cert** (same as A) — corrected after CF docs review. CF only treats the origin as valid HTTPS when the cert chains to a public CA; self-signed is rejected. |
| **C** | **HTTP origin behind an SG locked to the CloudFront managed prefix list** (`com.amazonaws.global.cloudfront.origin-facing`). No origin cert, simpler. Risk: traffic CF→origin is plaintext on the public internet. |
| **D** | **HTTP origin in a VPC + CF VPC origin** (the GA 2024 feature). Eliminates public IP entirely. Largest infra lift (subnets, NAT, VPC endpoints). |

**Recommendation: A (= B') for P1, with C considered for P2 *only* if the LE-IP
renewal cost is judged unacceptable.** A keeps "ports use TLS end-to-end" as the
fleet principle (`e4b55c6` §6). It does mean the LE-IP cert lifecycle still runs at
the origin — but since we are inside the SG locked to the CF prefix list, that cert
is invisible to the outside world. **D is out of scope for this brief** — VPC origin
is the right answer eventually but it is its own infra brief.

### Q3 — Hosted zone strategy?

| Opt | Position |
|-----|----------|
| **A** | **One pre-created zone per repo**, e.g. `vault.sgraph.ai`. Per-stack subdomain `<stack>.vault.sgraph.ai`. Zone lives forever; records come and go with stacks. |
| **B** | **Per-stack zone**. Creates a zone on `create`, deletes on `destroy`. Heavy, ~$0.50/zone/month flat charge, NS delegation dance. |
| **C** | **No zone — manual record on a user-supplied zone**, with a `--dns-zone-id` CLI flag. Caller owns DNS; we just create/delete a record. |

**Recommendation: A, with C as an escape hatch.** A is the only model that gives a
stable, deterministic hostname per stack. The zone must be pre-created out of band
(infrastructure brief, one-time `aws route53 create-hosted-zone` + delegation at the
registrar). The spec stores `vault_app__hosted_zone_id` in an SSM Parameter (or
config) so the service code reads it at `create`. C is supported as a flag for users
who want to point a different zone at the stack.

TTL: **60 s on the A/AAAA record**. Stacks are short-lived; we want clients not to
cache stale records past stack destroy.

### Q4 — ACM cert lifecycle?

| Opt | Position |
|-----|----------|
| **A** | **Per-stack cert**, created on `create`, deleted on `destroy`. DNS-01 validation via Route 53. Adds 2–5 min to `create` (DNS propagation + ACM validation). |
| **B** | **Wildcard cert** (`*.vault.sgraph.ai`), issued once, reused by all stacks. Lives forever. Faster `create`, simpler tear-down. |
| **C** | **Two-tier:** wildcard for `dns-only` mode (fast), per-stack for `cloudfront` mode (CF wants a cert in us-east-1 anyway). |

**Recommendation: B (wildcard) for both modes.** A single wildcard `*.vault.sgraph.ai`
in **us-east-1** (CF's home region) covers every per-stack subdomain. Issued once,
DNS-01 auto-renew handled by ACM, zero per-stack ACM work. Cert retention is decoupled
from stack lifecycle. Trade-off: wildcard cert means a compromised stack's TLS keys
could impersonate any subdomain — acceptable given each stack already runs the same
trust boundary (the user's own AWS account).

For CF: CF *requires* the cert to live in us-east-1 regardless of the distribution's
edge region. ACM is global-API but cert resources are per-region; we provision the
wildcard once in us-east-1 as part of the one-time zone setup.

### Q5 — Cache policy when CloudFront is in front?

| Opt | Position |
|-----|----------|
| **A** | **CachingDisabled managed policy** — forward everything, cache nothing. CF is purely a TLS terminator + name. |
| **B** | **Cache static assets only** — `OriginRequestPolicy=AllViewer`, `CachePolicy=CachingOptimized`, but a behaviour for `/` and `/api/*` set to no-cache. |
| **C** | **Tiered**: cache `/assets/*`, `/static/*` aggressively; everything else no-cache; forward `X-API-Key`, `x-sgraph-access-token` cookie, and the `?access_token=` query string in `OriginRequestPolicy`. |

**Recommendation: A.** Vault content is auth-gated and the access-token query string
is **dangerous to cache** (a 200 OK keyed by token leaks the token's view to the next
request). Disable caching globally; treat CF as a TLS gateway + name. If asset caching
becomes a measurable win later, file a follow-up brief (Q5-followup).

**Mandatory forwards** in the CF behaviour (CachingDisabled does this by default but
must be explicit in code): `Authorization` header, `X-API-Key` header, `Cookie`
header (so `x-sgraph-access-token` survives), and the `access_token` query string.
**Forbid** cache key inclusion of the auth fields — they are forwarded-not-keyed.

### Q6 — Stack-create orchestration order?

| Opt | Position |
|-----|----------|
| **A** | **Sequential, fail-fast**: EC2 → wait for public IP → ACM (skip if wildcard exists) → CF distribution → wait CF deployed → Route 53 alias → done. ~18 min worst case. |
| **B** | **Parallel where possible**: spin EC2 + CF together, R53 record once both ready. Less wall-clock, more failure-mode complexity. |
| **C** | **Async**: `create` returns immediately with `pending`, status endpoint polls each resource. Requires a status state machine. |

**Recommendation: A** in CloudFront mode, accepting the ~18-min create. CF is
inherently slow; pretending otherwise hides cost. In `dns-only` mode the path is
EC2 → ACM-wildcard-already-exists → R53 record → done, ~3 min total.

`destroy` order is the reverse and equally critical:

```
R53 record delete           (instant, propagation ~60s)
CF distribution disable     (~15-20 min, AWS hard-coded)
CF distribution delete      (immediate after disabled)
ACM cert keep               (wildcard, shared)
EC2 terminate + SG delete   (existing path)
```

**P1 acceptance: do not block `destroy` on CF disable.** Issue `DisableDistribution`,
mark the stack as `terminating`, return. A background reaper handles the final delete.
(Today's `delete_stack` is synchronous and returns in seconds — `destroy` must not
regress.)

### Q7 — `osbot-aws` coverage?

Verified — `osbot-aws` in this repo today imports cover EC2, IAM_Role, Parameter,
AWS_Config, Create_Image_ECR. No Route 53, ACM, or CloudFront helpers are imported
**anywhere** in `sg_compute*`. Three options for new AWS surface:

| Opt | Position |
|-----|----------|
| **A** | **Add new `osbot-aws` helpers upstream** (`Route53`, `ACM`, `CloudFront`), wait for release, then import. |
| **B** | **Narrow boto3 exception** in a new `Vault_App__Edge__Client` (or shared `Edge__AWS__Client`), mirroring the existing precedent (`Vault_App__AWS__Client` has STS, `Elastic__AWS__Client` is entirely boto3 with a documented header). |
| **C** | **Hybrid**: use osbot-aws where it exists, boto3 with a documented exception per file otherwise. |

**Recommendation: B + future upstream.** Add a new `sg_compute/platforms/dns/` and
`sg_compute/platforms/edge/` with documented boto3 boundaries (header comment per
file, identical pattern to the existing `EC2__SG__Helper` / `Vault_App__AWS__Client`).
File the upstream osbot-aws follow-up as a brief, do not block on it. CLAUDE.md
explicitly allows "narrow documented exceptions" for cases not covered by osbot-aws.

### Q8 — Naming?

The existing `Stack__Naming` (`sg_compute/platforms/ec2/helpers/Stack__Naming.py`)
gives `aws_name_for_stack` (no double-prefix) and `sg_name_for_stack` (no `sg-`
prefix). Extend with two new methods on the same class:

```
cf_name_for_stack(stack)       → "{prefix}-{stack}-cf"   e.g. "va-quiet-fermi-cf"
r53_record_for_stack(stack)    → "{stack}.{zone_name}"   e.g. "quiet-fermi.vault.sgraph.ai"
```

No new naming class — extending the existing one keeps the rule-14/rule-15 invariants
in one place. **Recommendation: extend `Stack__Naming`.**

---

## 4. Proposed architecture

### Request flow — `cloudfront` mode

```
                                                              ┌──────────────────┐
  client                                                      │  AWS Route 53    │
   │                                                          │  vault.sgraph.ai │
   │  GET https://quiet-fermi.vault.sgraph.ai/info/health     │  (hosted zone)   │
   │      Cookie: x-sgraph-access-token=…                     └──────────────────┘
   ▼                                                                   ▲
  ┌─────────┐    A-alias    ┌─────────────────┐                        │
  │ R53 DNS │──────────────►│ CloudFront      │                        │ alias
  │ resolve │               │ distribution    │                        │ record
  └─────────┘               │ d123abc.cf.net  │                        │
                            │                 │                        │
                            │  ACM cert       │◄───────────────────────┘
                            │  (us-east-1)    │
                            │  *.vault.sg…    │
                            └────────┬────────┘
                                     │ https://<eip>/…
                                     │ (Origin: HTTPS,
                                     │  cert = LE-IP cert
                                     │  on EC2)
                                     ▼
                            ┌─────────────────┐         ┌────────────────────┐
                            │  EC2 vault-app  │         │  SG: ingress       │
                            │  public IP/EIP  │         │  443/tcp from      │
                            │                 │         │  cloudfront prefix │
                            │  ┌───────────┐  │         │  list only         │
                            │  │ uvicorn   │  │         └────────────────────┘
                            │  │ TLS=on    │  │
                            │  │ :443 (LE) │  │
                            │  └───────────┘  │
                            │  ┌───────────┐  │
                            │  │ sg-send-  │  │
                            │  │ vault     │  │
                            │  └───────────┘  │
                            └─────────────────┘
```

### Request flow — `dns-only` mode (recommended default for ephemeral)

```
  client ──► R53 ──► A-record (IP) ──► https://<eip>/  (in-app uvicorn TLS,
                                                          ACM cert via DNS-01
                                                          for the hostname,
                                                          OR — see note —
                                                          existing LE-IP cert)
```

**Note on `dns-only` mode and certs:** ACM-issued certs cannot be exported and
installed on a non-AWS-managed endpoint (an EC2 you control directly). Two ways to
get a hostname cert onto the box:

1. Switch ACME flow from `letsencrypt-ip` (IP SAN) to `letsencrypt-dns` (DNS-01 via
   Route 53). The existing `Cert__ACME__Client` already speaks ACME; adding a DNS-01
   challenge plugin against Route 53 is the new piece.
2. Continue with `letsencrypt-ip` and accept that the hostname's cert mismatches.
   **Rejected** — defeats the purpose of the hostname.

So `dns-only` mode requires adding **DNS-01-via-Route53** to the existing TLS
library — a meaningful but well-scoped extension.

### Request flow — `none` mode (today, unchanged)

```
  client ──► https://<public_ip>/…  (LE-IP cert, validated via http-01)
```

---

## 5. Component breakdown

### New modules (proposed)

All under `sg_compute/platforms/` to match the existing TLS / EC2 layout. One class
per file. `Type_Safe` everywhere. No raw primitives. No Pydantic. No Literals
(use `Enum__*`).

#### `sg_compute/platforms/dns/`

| File | Responsibility |
|------|----------------|
| `Route53__Client.py`        | Sole boto3 boundary for Route 53. Methods: `find_hosted_zone_by_name`, `upsert_a_alias_record`, `upsert_a_record`, `delete_record_set`. Documented boto3 exception header. |
| `Schema__DNS__Record.py`    | `{zone_id, name, type, target, ttl, alias_target}` — pure data. |
| `Schema__DNS__Hosted_Zone.py` | `{zone_id, name}` — pure data. |
| `Enum__DNS__Record__Type.py` | `A`, `AAAA`, `CNAME`, `ALIAS_A` — no Literals. |

#### `sg_compute/platforms/edge/`

| File | Responsibility |
|------|----------------|
| `ACM__Client.py`             | Sole boto3 boundary for ACM. Methods: `find_wildcard_cert_in_us_east_1`, `request_certificate` (for per-stack mode, behind a flag — wildcard is the default), `wait_for_validation`. |
| `CloudFront__Client.py`      | Sole boto3 boundary for CloudFront. Methods: `create_distribution`, `wait_for_deployed`, `disable_distribution`, `delete_distribution`, `get_managed_prefix_list_id` (`com.amazonaws.global.cloudfront.origin-facing`). |
| `CloudFront__Distribution__Builder.py` | Builds the distribution config dict — origin, behaviour (CachingDisabled), aliases, ACM cert ARN, HTTP→HTTPS redirect, min TLS version. **Pure builder, no AWS calls** — unit-testable in-memory. |
| `Schema__Edge__Mode.py` & `Enum__Edge__Mode.py` | `NONE`, `DNS_ONLY`, `CLOUDFRONT`. |
| `Schema__Edge__Distribution.py` | `{distribution_id, domain_name, status, alias, cert_arn}` — pure data. |
| `Schema__Edge__Stack.py`      | What the spec records about a stack's edge config: `{mode, hostname, distribution_id, record_set_id, cert_arn}`. |

#### `sg_compute/platforms/tls/` (extend, not new)

| File | Change |
|------|--------|
| `Cert__ACME__Client.py`    | Add **DNS-01 via Route 53** flow (uses `Route53__Client.upsert_record` for the `_acme-challenge` TXT). Existing http-01 path unchanged. |
| `Enum__Cert__Mode.py`      | Add `LETSENCRYPT_DNS` to the existing `SELF_SIGNED` / `LETSENCRYPT_IP`. |
| `cert_init.py`             | Dispatch on the new mode, drive DNS-01 flow when set. |

### Existing modules — changes (proposed)

| File | Change |
|------|--------|
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Create__Request.py` | Add `edge_mode: str = 'none'`, `dns_zone_id: str = ''`, `hostname_subdomain: str = ''` (blank → auto from `stack_name`). |
| `sg_compute_specs/vault_app/service/Vault_App__Service.py` | New `_provision_edge(...)` helper called after `run_instance` when `edge_mode != 'none'`. Mirror existing fail-fast style. `delete_stack` gains an edge tear-down step (R53 delete → CF disable async). |
| `sg_compute_specs/vault_app/service/Vault_App__AWS__Client.py` | Adds composition of new `Route53__Client`, `ACM__Client`, `CloudFront__Client` (still one AWS boundary per spec). |
| `sg_compute_specs/vault_app/service/Vault_App__Stack__Mapper.py` | New tags `StackEdgeMode`, `StackHostname`, `StackDistributionId`. `vault_url` uses hostname when set (`https://<hostname>`) — falls back to `https://<ip>` otherwise. |
| `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Info.py` | Add `edge_mode: str = ''`, `hostname: str = ''`, `distribution_id: str = ''`, `distribution_status: str = ''`. |
| `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py` | No changes for `cloudfront` mode (origin keeps LE-IP cert). For `dns-only`, pass `tls_mode='letsencrypt-dns'` + the resolved hostname through to cert-init. |
| `sg_compute/platforms/ec2/helpers/Stack__Naming.py` | New `cf_name_for_stack`, `r53_record_for_stack` methods per Q8. |
| `sg_compute/platforms/ec2/helpers/EC2__SG__Helper.py` | New `ensure_security_group__cloudfront_prefix` method that opens `:443` to the managed `com.amazonaws.global.cloudfront.origin-facing` prefix list (replacing world-open in CF mode). |

### Modules that **must not** change

- The Playwright service (`sgraph_ai_service_playwright/`) — boundary-untouched.
- `Step__Executor`, `JS__Expression__Allowlist`, `Artefact__Writer` — untouched.
- The §8.2 TLS launch contract (`Fast_API__TLS__Launcher`) — untouched. CF mode
  hands the same in-app uvicorn TLS its cert; it just happens to also have CF in
  front.

---

## 6. AWS resources

| Resource | osbot-aws helper today | Naming pattern | Lifecycle owner |
|----------|------------------------|----------------|-----------------|
| Hosted zone `vault.sgraph.ai`     | **none** — boto3 narrow exception in `Route53__Client` | n/a (manual) | one-time bootstrap; **not** created per stack |
| ACM cert `*.vault.sgraph.ai` (us-east-1) | **none** — `ACM__Client` (boto3 boundary) | `vault-wildcard-cert` | one-time bootstrap; auto-renew by ACM |
| EC2 instance | `osbot_aws.aws.ec2.EC2` via existing `EC2__Launch__Helper` | `aws_name_for_stack(stack_name)` (e.g. `va-quiet-fermi`) | per-stack create/destroy |
| Security group | existing `EC2__SG__Helper` | `sg_name_for_stack(stack_name)` (e.g. `va-quiet-fermi-sg`) | per-stack create/destroy |
| Elastic IP (new, optional)         | **none** — `EC2__EIP__Helper` (proposed) | `aws_name_for_stack(stack_name)+'-eip'` | per-stack — **only if** CF origin pinning needed. P1 can skip and use the auto-assigned public IP. |
| Route 53 A/alias record           | **none** — `Route53__Client` | `r53_record_for_stack(stack_name)` (e.g. `quiet-fermi.vault.sgraph.ai`) | per-stack create/destroy |
| CloudFront distribution           | **none** — `CloudFront__Client` | `cf_name_for_stack(stack_name)` (e.g. `va-quiet-fermi-cf`) — set as the `Comment` field since CF distributions have no `Name` | per-stack create / async-destroy |

**Tag convention** on every new AWS resource: same `sg:purpose=vault-app`,
`sg:stack-name=<stack>`, `sg:allowed-ip=<caller-ip>`, `sg:creator=<creator>`
existing pattern. CF distributions support tagging — use it for stack lookup on
list/destroy.

---

## 7. Phased rollout

### P0 — Manual hostname pointing at IP (no Dev work)

**Scope:** prove the cert + hostname flow end-to-end **outside** the codebase first.

1. One-time bootstrap (operator): create the `vault.sgraph.ai` Route 53 hosted zone;
   delegate from the registrar; create the wildcard ACM cert in us-east-1 with
   DNS-01 validation.
2. Manually create an A-record for one running stack pointing at its public IP.
3. Manually swap the EC2's `tls_mode` from `letsencrypt-ip` to `letsencrypt-dns`
   for the hostname.
4. Verify browser-trusted HTTPS via the hostname.

**Acceptance:** `https://test.vault.sgraph.ai` (hand-pointed at a live stack) shows
no browser warning. **No code merged.**

### P1 — `dns-only` mode automated in `sp vault-app create`

**Scope:** add the DNS layer and DNS-01 cert path; no CloudFront yet.

1. `Route53__Client` shipped.
2. `Cert__ACME__Client` gains DNS-01 path; `Enum__Cert__Mode.LETSENCRYPT_DNS`.
3. `Schema__Vault_App__Create__Request.edge_mode` accepts `none` | `dns-only`.
4. `Vault_App__Service.create_stack` provisions the R53 record post-launch and
   passes hostname + `letsencrypt-dns` through cert-init.
5. `Vault_App__Service.delete_stack` deletes the R53 record on destroy.
6. `Vault_App__Stack__Mapper` surfaces `hostname` in info; `vault_url` prefers it.

**Acceptance:**
- `sp vault-app create --edge-mode dns-only` returns within ~3 min.
- `vault_url` is `https://<stack>.vault.sgraph.ai`.
- Curl shows ACM-issued cert chain, no warning.
- `sp vault-app delete` cleans up the R53 record (verified by AWS API).

### P2 — `cloudfront` mode automated in `sp vault-app create`

**Scope:** CloudFront in front; origin pinning; async tear-down.

1. `CloudFront__Client` + `CloudFront__Distribution__Builder` shipped.
2. `EC2__SG__Helper.ensure_security_group__cloudfront_prefix` shipped.
3. `Schema__Vault_App__Create__Request.edge_mode` extended to `cloudfront`.
4. `create_stack` orchestrates per §3 Q6 Option A; create returns when CF reports
   `Deployed` (~15–18 min). Make `--wait` honour this; `create` without `--wait`
   returns `pending` and the user polls.
5. `delete_stack` issues `DisableDistribution`, marks status `terminating`, returns.
   A background reaper (or a `sp vault-app reap` CLI) finishes once the CF is
   `Disabled`.

**Acceptance:**
- `sp vault-app create --edge-mode cloudfront --wait` completes within 20 min,
  returns a working `https://<stack>.vault.sgraph.ai`.
- Origin SG only allows the CF prefix list — verified by attempting direct EC2
  access and getting connection refused.
- `sp vault-app delete` returns in seconds; `sp vault-app list` shows the stack
  as `terminating` with a CF status field; reaper eventually clears it.

---

## 8. Risks & mitigations

| # | Risk | Mitigation |
|---|------|------------|
| R1 | CF create takes ~15 min, blocks user feedback | `--wait` is opt-in; non-wait path returns `pending` with status URL. CF `Deployed` is polled, not blocked-on by `create_stack`. |
| R2 | CF delete is async (~15-20 min); `destroy` could fail mid-way and leak a distribution | Background reaper + `sp vault-app reap` CLI. List operations report distributions whose tagged stack no longer exists. |
| R3 | Wildcard cert in a single region (us-east-1) — outage there blocks all stack creates | Accepted. ACM has very high availability. Mitigation if we ever care: maintain a backup cert in a second region (out of scope). |
| R4 | DNS-01 challenge needs Route 53 write at issue time — IAM permission widens | Scope the IAM role to **`route53:ChangeResourceRecordSets`** on the single zone only. Document the policy in the bootstrap step. |
| R5 | DNS propagation race — record visible to Let's Encrypt but ACME validates before TTL elapses | The `Cert__ACME__Client` DNS-01 path must poll public resolvers for the TXT before invoking ACME — standard ACME-client behaviour. |
| R6 | Origin IP leaks via `vault_url` in stale logs or info dumps | When `edge_mode != 'none'`, the `vault_url` returned to callers is the hostname; the public IP stays in the info schema for ops but is *not* the canonical URL. Document in the info renderer. |
| R7 | CF caches an `access_token`-bearing response under another caller's view | **CachingDisabled** is mandatory (Q5). Add a unit-test on `CloudFront__Distribution__Builder` that asserts the CachePolicyId equals the AWS-managed `CachingDisabled` UUID. |
| R8 | Cost surprise — CF distributions are free at low traffic but data-transfer-out is billed | Document in the CLI help. Per-stack distributions for ephemeral test stacks add up; default `--edge-mode none` keeps the bill at zero. |
| R9 | `osbot-aws` lacks helpers — direct boto3 expands | Documented narrow exception per file (same pattern as today's `EC2__SG__Helper`). File a follow-up brief to upstream the Route53/ACM/CF helpers. |
| R10 | Hosted-zone-id discovery at runtime requires `route53:ListHostedZones` IAM | Cache the zone-id in an SSM Parameter at bootstrap; runtime reads the Parameter (already-used pattern). |

---

## 9. Test plan sketch

The deploy-via-pytest convention in this repo numbers tests `test_N__…` and runs
them top-down. For the new edge surface, two test tracks:

### Track A — unit / in-memory (no AWS, mandatory)

| Test file | Asserts |
|-----------|---------|
| `sg_compute__tests/platforms/dns/test_Route53__Client.py`       | (boundary-only) construction; AWS calls mocked at the boto3-client level using a `Route53__Client__In_Memory` subclass in tests/unit (no `mock` module — same pattern as `Elastic__AWS__Client__In_Memory`). |
| `sg_compute__tests/platforms/edge/test_CloudFront__Distribution__Builder.py` | (pure logic, in-memory) distribution dict has CachingDisabled, aliases match hostname, origin is HTTPS, min-TLS is `TLSv1.2_2021`, viewer→https-only. |
| `sg_compute__tests/platforms/edge/test_ACM__Client.py`          | wildcard lookup returns the in-memory cert by `*.vault.sgraph.ai` SAN. |
| `sg_compute__tests/platforms/tls/test_Cert__ACME__Client__dns01.py` | DNS-01 path drives `Route53__Client.upsert_record` with a TXT under `_acme-challenge.<host>`; polls; cleans up on success/failure. |
| `sg_compute_specs/vault_app/tests/test_Schema__Vault_App__Create__Request.py` | new `edge_mode` field default = `'none'`; enum value validation. |
| `sg_compute_specs/vault_app/tests/test_Vault_App__Stack__Mapper.py` | `vault_url` prefers hostname when set; falls back to IP. |
| `sg_compute_specs/vault_app/tests/test_Vault_App__Service__cli_surface.py` | new flags wired through to schema. |

No mocks, no patches — `register_*__in_memory` composition style used throughout
the repo.

### Track B — deploy-via-pytest (real AWS, gated)

Numbered top-down, mirroring the existing lambda/EC2 deploy patterns. Gate on
`SG_PLAYWRIGHT__AWS_DEPLOY_TESTS=1` to skip in normal CI.

```
test_1__bootstrap__hosted_zone_exists
test_2__bootstrap__wildcard_cert_exists
test_3__create__dns_only_mode_returns_hostname
test_4__create__dns_only_mode_curl_hostname_returns_200
test_5__create__dns_only_mode_cert_chains_to_public_ca
test_6__list__shows_edge_mode_and_hostname
test_7__delete__r53_record_gone
test_8__delete__ec2_terminated
test_9__create__cloudfront_mode_returns_pending
test_10__create__cloudfront_mode_eventually_deployed
test_11__create__cloudfront_mode_origin_sg_locked_to_prefix_list
test_12__create__cloudfront_mode_direct_ec2_unreachable_by_caller_ip
test_13__create__cloudfront_mode_hostname_works
test_14__delete__cloudfront_mode_disables_distribution
test_15__reap__deletes_disabled_distribution
```

Each numbered test is a separate function; later tests assume earlier ones passed
(deploy ordering). State carries via a tmp-path fixture.

### What is **not** unit-testable

- The actual ACME exchange with Let's Encrypt (already documented in `8aad135` —
  needs a real public IP and the LE rate limit).
- CloudFront deployment latency (real CF behaviour).
- DNS propagation timing.

These ride with Track B and a manual verification checklist.

---

## 10. Next actions (decisions the user must make before Dev starts)

In order of blockingness:

1. **Q1** — confirm the three-mode model (`none` | `dns-only` | `cloudfront`) is
   the right shape, or argue for a different split.
2. **Q3** — name and pre-create the hosted zone. The brief assumes `vault.sgraph.ai`;
   the user picks the actual zone and seeds it (registrar delegation + ACM wildcard
   cert in us-east-1). Without this, P0 cannot start.
3. **Q4** — ratify the wildcard-cert strategy (one cert covers all stacks) vs
   per-stack certs. Strongly affects ACM permissions and `create_stack` latency.
4. **Q5** — confirm **CachingDisabled** is the right CF cache policy for vault-app
   (Architect's recommendation: yes; the access-token surface makes anything else
   dangerous).
5. **Q6** — accept the ~18-min `cloudfront`-mode `create` and the async `destroy`
   model, or scope CF mode out of P1 entirely.
6. **Q7** — sign off on the new `Route53__Client`, `ACM__Client`, `CloudFront__Client`
   as **boundary-only narrow boto3 exceptions**, with an upstream-osbot-aws
   follow-up brief filed separately.
7. **Q2** — origin TLS posture: confirm "HTTPS origin with the existing LE-IP cert"
   for P1; defer the SG-locked-to-CF-prefix tightening to P2.
8. **Scope** — confirm P0/P1/P2 split. Minimum viable Dev slice = **P1 only**
   (`dns-only` mode). P2 (CloudFront) is a follow-up.

When these are answered, the Dev contract is:

- The new modules in §5 are the slice.
- §6 is the resource table.
- §9 Track A is the test bar.
- The reality doc (`team/roles/librarian/reality/vault/index.md` once created) must
  be updated when the slice lands, marking `dns-only` and `cloudfront` modes as
  EXISTS and removing the PROPOSED label at the top of this brief.

---

*Filed by Architect (Claude), 2026-05-15. No code changed by this document — it is
a plan and a set of decisions for human ratification before Dev picks it up.
Builds on the TLS lineage: `e4b55c6` → `012adb0` → `d44863a` (research → design
→ Q6-resolved) → `27d5647` → `8aad135` → `9626e52` (P0 PoC → LE-IP wired → TLS
default). This brief is the deferred Option B2 / Q4 from `v0.2.6__vault-app-tls-options.md`.*
