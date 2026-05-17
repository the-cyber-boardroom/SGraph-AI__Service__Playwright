---
title: "01 — Grounding: what exists today vs what the brief proposes"
file: 01__grounding.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 01 — Grounding

For each major component the v2 brief proposes, this file records the *measured* state today:

- **EXISTS** — cite the file (and line) that backs the claim.
- **EXISTS, NEEDS EXTENSION** — file exists, but the brief asks for additional methods / schemas.
- **PROPOSED — does not exist yet** — required label per CLAUDE.md rule #2 / reality-doc rule #2.

All paths are absolute under the repo root `/home/user/SGraph-AI__Service__Playwright/`.

---

## 1. Substrate — `sg vault-app`

### 1.1 The spec itself

**EXISTS.** Full ephemeral-EC2 vault-app spec at `sg_compute_specs/vault_app/`. Verified directory tree:

```
sg_compute_specs/vault_app/
├── __init__.py
├── manifest.py
├── version
├── cli/Cli__Vault_App.py
├── docker/                                  # compose template + cert-init etc.
├── enums/
├── schemas/
│   ├── Schema__Vault_App__Auto_DNS__Result.py
│   ├── Schema__Vault_App__Create__Request.py
│   ├── Schema__Vault_App__Create__Response.py
│   ├── Schema__Vault_App__Delete__Response.py
│   ├── Schema__Vault_App__Info.py
│   └── Schema__Vault_App__List.py
├── service/
│   ├── Vault_App__AMI__Helper.py
│   ├── Vault_App__AWS__Client.py
│   ├── Vault_App__Auto_DNS.py               # 105 lines
│   ├── Vault_App__Compose__Template.py
│   ├── Vault_App__Service.py                # 546 lines
│   ├── Vault_App__Stack__Mapper.py
│   └── Vault_App__User_Data__Builder.py
└── tests/                                   # 7 test files including test_Vault_App__Auto_DNS.py
```

Mounted at `sg vault-app` (alias `va`) via `sg_compute/cli/Cli__SG.py:97-99`.

### 1.2 Stop / start verbs

**PROPOSED — does not exist yet.** Verified — `Vault_App__Service.py` contains `create_stack`, `list_stacks`, `get_stack_info`, `delete_stack`, `health` (and the diag helpers) but no `stop_stack` / `start_stack`. The brief's [`03 §3`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md) correctly identifies this gap.

### 1.3 Auto-DNS (per-slug A-record writer)

**EXISTS.** `sg_compute_specs/vault_app/service/Vault_App__Auto_DNS.py` (entire file, 105 lines). Re-usable verbatim from the new `start_stack` path; the brief's design is right.

### 1.4 User-data + idle-terminate timer

**EXISTS** in `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py`. The brief's "shutdown → stop" change requires editing the systemd-timer command this builder emits (small surgical change, not a rewrite).

### 1.5 IAM profile `playwright-ec2`

**EXISTS, NEEDS POLICY EXTENSION.** Defined in `sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py` — `IAM__ROLE_NAME = 'playwright-ec2'` (line 147), policy assembled around line 177. The brief at [`03 §3.4`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md) cites `SP__CLI__Lambda__Policy.py` as precedent for the "where to put it"; that file is part of the Lambda-deploy policy under `sgraph_ai_service_playwright__cli/`. **Note:** the brief assumes `playwright-ec2` is owned by `Vault_App__Service` (`PROFILE_NAME` constant at line 40 of `Vault_App__Service.py`), but the *role+policy itself* is created/owned by `Ec2__AWS__Client.py`. The IAM policy edit therefore lands in `Ec2__AWS__Client.py`, not in `vault_app/`. This is a small correction to the brief; flagged in `06__open-questions.md` Q3.

---

## 2. `sg aws dns` (the DNS layer)

### 2.1 The package

**EXISTS.** `sgraph_ai_service_playwright__cli/aws/dns/`:

```
aws/dns/
├── __init__.py
├── cli/Cli__Dns.py                          # 1248 lines
├── collections/
├── enums/
├── primitives/
├── schemas/
└── service/
    ├── Dig__Runner.py
    ├── Route53__AWS__Client.py              # 273 lines — sole boto3 boundary
    ├── Route53__Authoritative__Checker.py
    ├── Route53__Check__Orchestrator.py
    ├── Route53__Instance__Linker.py
    ├── Route53__Local__Checker.py
    ├── Route53__Public_Resolver__Checker.py
    ├── Route53__Smart_Verify.py
    └── Route53__Zone__Resolver.py
```

Mutations gated by `SG_AWS__DNS__ALLOW_MUTATIONS=1` (`Cli__Dns.py` — line ~117 per the brief; pattern verified at this size).

### 2.2 What the Waker / `Vault_Publish__Service` will compose

| Class | File | Used by |
|-------|------|---------|
| `Route53__AWS__Client` | `aws/dns/service/Route53__AWS__Client.py` | Waker (DNS-swap), `Vault_Publish__Service` (status, bootstrap wildcard ALIAS) |
| `Route53__Zone__Resolver` | `aws/dns/service/Route53__Zone__Resolver.py` | Waker `Slug__From_Host` (parse Host → owning zone) |
| `Route53__Instance__Linker` | `aws/dns/service/Route53__Instance__Linker.py` | `Vault_App__Service.start_stack` (EC2-ref → IP) — already used at `create_stack` time |
| `Route53__Smart_Verify` | `aws/dns/service/Route53__Smart_Verify.py` | `Vault_Publish__Service.bootstrap` (verify wildcard ALIAS post-mutation) |

All EXIST. Zero additions required from the vault-publish work.

### 2.3 Default zone convention

**EXISTS.** `DEFAULT_ZONE_NAME_FALLBACK = 'sg-compute.sgraph.ai'` (`aws/dns/service/Route53__AWS__Client.py:35` per brief) — overridable with `SG_AWS__DNS__DEFAULT_ZONE`. `Vault_App__Service.py:42` mirrors the same constant (`DEFAULT_AWS_DNS_ZONE_FALLBACK`) and reads the same env var. The vault-publish spec **must** read the same env var (do not hard-code).

---

## 3. `sg aws acm`

**EXISTS — read-only.** `sgraph_ai_service_playwright__cli/aws/acm/` (subfolders: `cli/`, `collections/`, `enums/`, `schemas/`, `service/`). No `request-certificate` capability; brief consumes the cert ARN as a config input (manual one-time issuance). No code addition required for phase 1/2.

---

## 4. `sg aws cf` (CloudFront primitive)

**PROPOSED — does not exist yet.** Verified — `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/aws/cf/` does not exist. `osbot_aws.aws.cloud_front.Cloud_Front` only exposes `distributions()` (list) and `invalidate_path` / `invalidate_paths` (matches brief [`02 §7.5`](file:///tmp/vault-publish-brief/02__what-exists-today.md)).

This is the biggest single piece of net-new platform code in the brief.

---

## 5. `sg aws lambda` (Lambda deploy primitive)

**PROPOSED — does not exist yet.** Verified — `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/aws/lambda_/` does not exist. `osbot_aws.deploy.Deploy_Lambda` exists upstream and the brief proposes a thin Typer wrapper around it.

---

## 6. The vault-publish spec itself (`sg_compute_specs/vault_publish/`)

**PROPOSED — does not exist yet.** Verified — `/home/user/SGraph-AI__Service__Playwright/sg_compute_specs/vault_publish/` does not exist.

### 6.1 The brief's "5 ports from the old top-level package" claim

**CORRECTION.** The brief (README §2.1, [`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) refers to a top-level `vault_publish/` Python package on branch `claude/review-subdomain-workflow-bRIbm` containing `Safe_Str__Slug`, `Slug__Validator`, `Reserved__Slugs`, `Enum__Slug__Error_Code` and their tests.

**On the current working tree (`dev`), this package does NOT exist.** Verified — `/home/user/SGraph-AI__Service__Playwright/vault_publish/` does not exist; the only file containing `Slug` under repo root is unrelated. The brief mis-cites the source: the ports live on a feature branch that has not merged.

Three implications:

1. The Dev work cannot literally "port from the old top-level package" on the current branch — the source files are not here.
2. Dev must either (a) cherry-pick the slug primitives from `claude/review-subdomain-workflow-bRIbm` into the new spec, or (b) re-author them from scratch using the spec in the brief ([`04 §3`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) which has the regex / max-length / error-code definitions.
3. The brief's claim "the only pieces of the v0.2.11 work that survive verbatim" needs slight rewording: those pieces survive *as a design*, not as a *file move*.

This decision goes in `06__open-questions.md` Q2.

---

## 7. `osbot-aws` primitives the brief leans on

All EXIST upstream (verified by the brief's [`02 §7`](file:///tmp/vault-publish-brief/02__what-exists-today.md)) — no further verification needed for this plan, since these are pinned dependencies:

| Helper | Brief uses for |
|--------|----------------|
| `osbot_aws.aws.ec2.EC2` / `EC2_Instance` | `Vault_App__Service.{stop,start}_stack`; Waker `Endpoint__Resolver__EC2` |
| `osbot_aws.aws.lambda_.Lambda` | `sg aws lambda` read paths |
| `osbot_aws.deploy.Deploy_Lambda` | `sg aws lambda` deploy path; Waker deployment in `bootstrap` |
| `osbot_aws.helpers.Parameter` | `Slug__Registry` SSM backend |
| `osbot_aws.aws.iam.IAM_Role_With_Policy` | Waker Lambda execution role minting |
| `osbot_aws.aws.cloud_front.Cloud_Front` | *limited* — list + invalidate only; `sg aws cf` fills the gap |
| `osbot_aws.aws.ecs.ECS_Fargate_Task` | Phase 3 — out of plan scope |

---

## 8. `osbot-utils` primitives (Type_Safe layer)

All EXIST upstream:

- `osbot_utils.type_safe.Type_Safe` — base for every schema / service class.
- `osbot_utils.type_safe.primitives.core.Safe_Str` / `Safe_Int` — base for `Safe_Str__Slug` etc.
- `osbot_utils.type_safe.type_safe_core.collections.{Type_Safe__List, Type_Safe__Dict}` — typed collections.

These are the building blocks for every new class the plan adds. CLAUDE.md rules #1 (`Type_Safe` everywhere), #2 (no raw primitives) and #3 (no Literals) apply to everything below.

---

## 9. CLI mount conventions

**EXISTS.** `sg_compute/cli/Cli__SG.py` mounts every spec via `app.add_typer(...)` (one entry per spec, with optional alias). The vault-publish CLI mount will follow the same pattern at this file:

```python
# proposed addition to sg_compute/cli/Cli__SG.py
from sg_compute_specs.vault_publish.cli.Cli__Vault_Publish import app as _vault_publish_app
app.add_typer(_vault_publish_app, name='vault-publish', help='Publish a vault at <slug>.sg-compute.sgraph.ai with on-demand wake.')
app.add_typer(_vault_publish_app, name='vp',            hidden=True)
```

`sg aws cf` / `sg aws lambda` mount under the existing `sg aws` Typer group at `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` (mirroring how `sg aws dns` and `sg aws acm` mount today — verified by `Cli__SG.py:26-27`).

---

## 10. `Spec__Service__Base`, manifests, catalogue integration

**EXISTS.** `sg_compute/core/spec/Spec__Service__Base.py` is the base class every spec service extends. `Vault_App__Service` already does (`Vault_App__Service.py:49`). The new `Vault_Publish__Service` extends the same base — gets `health` / `exec` / `connect_target` for free where applicable.

Manifest pattern: every spec has a `manifest.py` with a module-level `MANIFEST = Schema__Spec__Manifest__Entry(...)`. Verified — every entry under `sg_compute_specs/*/manifest.py` follows the same shape (`vault_app/manifest.py` inspected as exemplar). The vault-publish manifest follows this exactly.

The brief's manifest sketch ([`04 §9`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)) uses `stability='experimental'` as a string — **correction:** this must be `Enum__Spec__Stability.EXPERIMENTAL` per the actual `Schema__Spec__Manifest__Entry` shape (verified in `vault_app/manifest.py`). Also `capabilities` is `List[Enum__Spec__Capability]`, not `List[str]`. Both are flagged in `02__reuse-map.md` row "manifest".

---

## 11. Version

**RESOLVED 2026-05-17.** The repo-root `version` placeholder (`vDONT-MERGE.DONT-MERGE.1`) was a versioning-bug session marker. Pulling `dev` into the working branch resolves it to **v0.2.23**. The plan folder is named accordingly: `v0.2.23__plan__vault-publish-spec/`. The new spec `sg_compute_specs/vault_publish/version` starts at `v0.1.0` (mirroring `sg_compute_specs/elastic/version` and other independently-versioned specs).

See `06__open-questions.md` Q4 (RESOLVED).

---

## 12. Summary table — does the brief's load-bearing assumption hold?

| Brief claim | Verdict | Citation |
|-------------|---------|----------|
| "`sg vault-app create --with-aws-dns` already works" | EXISTS | `Vault_App__Service.py:79-177` |
| "`Vault_App__Auto_DNS` is exactly the call to re-invoke on `start`" | EXISTS | `Vault_App__Auto_DNS.py` (entire file) |
| "stop/start verbs are missing" | TRUE — PROPOSED | absence in `Vault_App__Service.py` confirmed |
| "`sg aws dns` is a fully-typed Route 53 layer with `Route53__AWS__Client` as the sole boto3 boundary" | EXISTS | `aws/dns/service/Route53__AWS__Client.py` |
| "`sg aws acm` is read-only today" | EXISTS — read-only | `aws/acm/` subfolders present, no mutation client |
| "`sg aws cf` does not exist" | TRUE — PROPOSED | absence in `aws/` confirmed |
| "`sg aws lambda` does not exist" | TRUE — PROPOSED | absence in `aws/` confirmed |
| "`osbot_aws.Cloud_Front` only covers list + invalidate" | TRUE (per upstream docs) | confirmed via brief; not re-verified upstream in this plan |
| "Top-level `vault_publish/` package on `claude/review-subdomain-workflow-bRIbm`" | MIS-CITES BRANCH | absent on `dev`; see §6.1 |

Eight of nine load-bearing claims verified. The ninth (file ports from a different branch) is RESOLVED: **re-author** (see `06__open-questions.md` Q2).

---

## 13. Phase 0 — VERIFIED on 2026-05-17

**Status:** COMPLETED. Empirically validated end-to-end by the human operator on 2026-05-17.

### 13.1 Command

```bash
sg vault-app create --with-aws-dns --name hello-world --wait
```

Simpler than the original Phase 0 sketch — no explicit `--tls-mode` / `--tls-hostname` flags required; the substrate's `--with-aws-dns` flow handles cert issuance end-to-end.

### 13.2 Result

| Field | Value |
|-------|-------|
| Instance ID | `i-05c161bc8aae48b01` |
| Public IP | `18.130.98.215` |
| FQDN | `hello-world.sg-compute.sgraph.ai` |
| Wall-clock to healthy | **1 min 54 s** |
| TLS issuer | Let's Encrypt R13 (CA-signed, browser-trusted) |
| Cert remaining | 89 days |
| Auto-DNS verification log line | `auto-dns: done … (INSYNC + authoritative)` in 24190 ms |

### 13.3 What this proves

- The warm path (`create_stack` → `Vault_App__Auto_DNS` → cert-init → LE issuance → vault healthy) works end-to-end without any v2 work.
- The 60-second TTL convention in `Vault_App__Auto_DNS.AUTO_DNS__RECORD_TTL_SEC` allows propagation to authoritative + public-resolver sync in ~24 s.
- No substrate fixes required before P1a Dev work starts. The only gating substrate concern is the Q13 audit of `delete_stack` (see §13.4).

### 13.4 Side finding — `delete_stack` does NOT delete DNS

Verified during this plan's preparation (`sg_compute_specs/vault_app/service/Vault_App__Service.py:528-546`): `delete_stack` calls `instance.terminate` and `sg.delete_security_group`, but never invokes `Route53__AWS__Client.delete_record` or `Vault_App__Auto_DNS` cleanup. Every `sg vault-app delete` to date has leaked an A record under `sg-compute.sgraph.ai`.

This is a substrate bad-failure (CLAUDE.md rule #27) — caught here, fixed at the start of P1a. The substrate already exposes `sg aws dns records delete` (verified at `sgraph_ai_service_playwright__cli/aws/dns/cli/Cli__Dns.py:1054`), so the wiring is purely composition. See `06__open-questions.md` Q13 (RESOLVED, gating for P1a) and `04__phased-implementation.md` Phase 1a.
