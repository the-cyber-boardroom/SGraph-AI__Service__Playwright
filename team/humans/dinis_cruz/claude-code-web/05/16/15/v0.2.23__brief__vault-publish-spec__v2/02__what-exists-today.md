---
title: "02 — What exists today"
file: 02__what-exists-today.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 02 — What exists today

A file-cited inventory of every piece this spec is going to compose. Three sources: this repo, `osbot-aws`, and `osbot-utils`. Read this before agreeing to the work in [`03`](03__sg-compute-additions.md) and [`04`](04__vault-publish-spec.md) — most of the heavy lifting is already done.

---

## 1. This repo — `sg vault-app` (the substrate)

A full ephemeral-EC2 vault-app spec exists at `sg_compute_specs/vault_app/`. It is the substrate the vault-publish spec sits on top of.

### 1.1 CLI surface (mounted as `sg vault-app`)

| Verb | Source | Behaviour |
|------|--------|-----------|
| `create` | `Vault_App__Service.create_stack` (`service/Vault_App__Service.py:79-177`) | Launches an EC2 with the vault-app stack, optional `--with-playwright` / `--with-tls-check` / `--with-aws-dns`; auto-terminate timer; auto-DNS A record |
| `list` | `Vault_App__Service.list_stacks` (`service/Vault_App__Service.py:179-183`) | Tag-based discovery (`tag:StackType=vault-app`) |
| `info` | `Vault_App__Service.get_stack_info` (`service/Vault_App__Service.py:185-187`) | `Schema__Vault_App__Info` |
| `delete` | `Vault_App__Service.delete_stack` (`service/Vault_App__Service.py:528-546`) | Terminates EC2 + deletes SG. **Does not delete DNS record** |
| `health` / `wait` / `exec` / `connect` / `logs` / `extend` / `diag` / `open` / `recreate` / `ami` / `cert` | various | Full operator surface (covered in the v0.2.6 vault-app arch-plan) |

**Missing for our wake flow:** `stop` and `start`. There is no verb today that stops an EC2 without terminating it. See [`03 §3`](03__sg-compute-additions.md#3-extend-sg-vault-app-with-stop-and-start).

### 1.2 The shipped compose stack

`sg_compute_specs/vault_app/docker/compose/docker-compose.yml` + rendered dynamically by `Vault_App__Compose__Template.render()` (`service/Vault_App__Compose__Template.py:160-186`):

| Container | Image | Port (external) | Purpose |
|-----------|-------|------------------|---------|
| `host-plane` | `{ECR}/sgraph_ai_service_playwright_host:{TAG}` | `127.0.0.1:19009` (SSM-forward only) | Container management API |
| `sg-send-vault` | `diniscruz/sg-send-vault:latest` | `8080` (plain) or `443` (TLS) | **The published vault site is served here** |
| `cert-init` (if `--with-tls-check`) | `{ECR}/sgraph_ai_service_playwright_host:{TAG}` | `80` (transient — ACME http-01) | One-shot LE cert issuance |
| `sg-playwright` (if `--with-playwright`) | `{ECR}/sgraph_ai_service_playwright:{TAG}` | `80` (after cert-init exits) | Browser automation REST API |
| `agent-mitmproxy` (if `--with-playwright`) | `{ECR}/agent_mitmproxy:{TAG}` | `127.0.0.1:19081` (SSM-forward only) | Passive traffic capture |

For vault-publish we only need the **just-vault** mode (host-plane + sg-send-vault). Playwright + mitmproxy are off by default.

### 1.3 Vault seeding — already wired

`sg-send-vault` reads `SG_VAULT_APP__SEED_VAULT_KEYS` (comma-separated keys) at boot and clones each vault via `sgit clone` into `/data`. Idempotent — skips keys whose vault already exists. The user-data builder writes this env var into the systemd unit (`Vault_App__User_Data__Builder.render(..., seed_vault_keys=...)`).

This is the "how does the right content land on the EC2" answer. The vault-publish spec passes the slug's vault key through here; no fetcher / verifier / interpreter is needed in our spec.

### 1.4 TLS — already wired

Three modes, controlled by `--tls-mode`:

- `self-signed` — cert-init generates a throwaway cert
- `letsencrypt-ip` — Let's Encrypt for the EC2 public IP (browser-trusted; valid for the IP only)
- `letsencrypt-hostname` — Let's Encrypt for an FQDN (requires the FQDN's A record to resolve to the EC2 before cert-init's DNS-wait window — `SG__CERT_INIT__DNS_WAIT_TIMEOUT_SEC=900s`)

`--with-aws-dns` auto-flips `--tls-mode letsencrypt-ip` → `letsencrypt-hostname` and derives `tls_hostname = <stack-name>.<default-zone>` (`Vault_App__Service.py:87-90`).

For vault-publish, every published slug runs in `--with-aws-dns --tls-mode letsencrypt-hostname` mode. Browsers get a real cert; no warnings.

### 1.5 Auto-terminate — already wired

`--max-hours N` writes a `TAG_TERMINATE_AT` tag and a `systemd-run --on-active=<N>h /sbin/shutdown -h now` timer on the instance. `extend N` resets it. `delete` terminates immediately.

For vault-publish we want **stop-instead-of-terminate** on idle, so the user-data hook needs a small change: when the timer fires, call `EC2.instance_stop` on this instance (via IMDSv2 → STS → EC2 from inside the box) rather than `/sbin/shutdown -h now`. That is part of [`03 §3`](03__sg-compute-additions.md#3-extend-sg-vault-app-with-stop-and-start).

---

## 2. This repo — `sg aws dns` (the DNS layer)

`sgraph_ai_service_playwright__cli/aws/dns/` — a fully-typed Route 53 layer.

### 2.1 CLI surface

| Verb | Source |
|------|--------|
| `sg aws dns zones list` | `Cli__Dns.zones_list` |
| `sg aws dns zone show / list / check` | `Cli__Dns.zone_show / zone_list / zone_check` |
| `sg aws dns records get / add / update / delete / check` | `Cli__Dns.records_*` |
| `sg aws dns instance create-record` | `Cli__Dns.instance_create_record` |

Mutations require `SG_AWS__DNS__ALLOW_MUTATIONS=1` (`Cli__Dns.py:117-121`). The `add` form is exempt because it is additive.

### 2.2 Service classes (reusable from the vault-publish spec)

| Class | Use in vault-publish |
|-------|-----------------------|
| `Route53__AWS__Client` (`service/Route53__AWS__Client.py`) | `upsert_record`, `delete_record`, `wait_for_change`, `get_record`. **Sole boto3 boundary** — header note says "Migrate to osbot-aws once Route 53 wrapper grows"; the wake Lambda will use this directly |
| `Route53__Instance__Linker` (`service/Route53__Instance__Linker.py`) | EC2-ref → `(instance, public_ip, name_tag)`. The Waker uses the same resolution shape |
| `Route53__Zone__Resolver` (`service/Route53__Zone__Resolver.py`) | FQDN → owning hosted zone (walks labels longest-first). The Waker uses this on the Host header |
| `Route53__Smart_Verify` (`service/Route53__Smart_Verify.py`) | Decides between authoritative-only and authoritative + public-resolver checks based on whether the record is `NEW_NAME` / `UPSERT` / `DELETE`. **The Waker should use it on cold→warm DNS-swap** to confirm authoritative-pass before proxying the next request |
| `Route53__Check__Orchestrator` + Authoritative / Public-Resolver / Local checkers | Underneath Smart_Verify; useful for the spec's `status` verb |
| `Dig__Runner` (`service/Dig__Runner.py`) | shell-out to `dig`; underpins the checkers |

### 2.3 The default-zone convention

`DEFAULT_ZONE_NAME_FALLBACK = 'sg-compute.sgraph.ai'` (`Route53__AWS__Client.py:35`), overridable with env `SG_AWS__DNS__DEFAULT_ZONE`. `Vault_App__Service` reuses the same env var (`Vault_App__Service.py:46`). **The vault-publish spec must read the same env** — never hard-code the zone.

---

## 3. This repo — `Vault_App__Auto_DNS` (the per-slug A-record writer)

`sg_compute_specs/vault_app/service/Vault_App__Auto_DNS.py` (entire file, ~100 lines).

What it does:

1. Resolves the FQDN's owning zone (`Route53__Zone__Resolver.resolve_zone_for_fqdn`)
2. `Route53__AWS__Client.upsert_record(zone, fqdn, 'A', [public_ip], ttl=60)`
3. Waits for `INSYNC` (`AUTO_DNS__INSYNC_TIMEOUT_SEC = 120s`, 2s poll)
4. Verifies via `Route53__Authoritative__Checker.check(...)`
5. Returns `Schema__Vault_App__Auto_DNS__Result(fqdn, public_ip, zone_id, zone_name, change_id, insync, authoritative_pass, elapsed_ms, error)`

Critical property: **never raises** — errors land in `result.error`. The CLI thread joins it after the EC2 health-wait returns.

This is exactly the call we need to re-invoke on `start` (when the EC2 comes back up with a new IP). Phase 1a wires it into `start_stack`.

---

## 4. This repo — `sg aws acm` (read-only today)

`sgraph_ai_service_playwright__cli/aws/acm/` — read-only listing + cert show. `ACM__AWS__Client` is the boto3 boundary.

For the vault-publish bootstrap we need a one-time `request-certificate` for the wildcard `*.sg-compute.sgraph.ai` in `us-east-1` (CloudFront's required region) with DNS validation. That can either:

- Be done manually one time and the ARN pinned in config (simplest)
- Or extended in the existing ACM client (`ACM__AWS__Client.request_dns_validated(...)`) — small addition.

This brief assumes **manual one-time bootstrap** for the ACM cert. Adding `sg aws acm request` is out of scope of phase 2; we just consume the ARN.

---

## 5. This repo — `sgraph_ai_service_playwright__cli/aws/Stack__Naming.py`

Section-aware AWS naming helpers shared across stacks: `aws_name_for_stack(stack_name)` avoids double-prefixing (e.g. `va-va-quiet-fermi` → `va-quiet-fermi`), `sg_name_for_stack(stack_name)` produces a security-group name that does NOT start with `sg-` (AWS rejects those).

The new `sg aws cf` primitive should reuse `Stack__Naming(section_prefix='cf')` for any per-distribution resource it creates (none today — distributions are global; this is forward-looking).

---

## 6. This repo — IAM `playwright-ec2` profile

`Vault_App__Service.PROFILE_NAME = 'playwright-ec2'` (`service/Vault_App__Service.py:40`) — every EC2 launched by vault-app is given this instance profile, which grants SSM + ECR access.

For our **idle-shutdown-as-stop** change (the box stops itself rather than terminates), we need to add `ec2:StopInstances` (with a `aws:ResourceTag/StackType=vault-app` condition) to the profile's policy. That is a one-line policy edit, tracked in [`03 §3.4`](03__sg-compute-additions.md#34-iam-policy-addition).

---

## 7. `osbot-aws` — what is already there (use directly)

### 7.1 EC2 lifecycle — the entire wake-side surface

| Helper | Methods we use |
|--------|-----------------|
| `osbot_aws.aws.ec2.EC2` | `instance_start(instance_id)`, `instance_stop(instance_id)`, `wait_for_instance_running(instance_id)`, `wait_for_instance_status_ok(instance_id)`, `wait_for_instance_stopped(instance_id)` |
| `osbot_aws.aws.ec2.EC2_Instance` | per-instance wrapper: `start()`, `stop()`, `state()`, `ip_address()`, `info()`, `wait_for_ssh()` — the Waker uses this |

These cover everything the wake Lambda needs to know about EC2 lifecycle. No new boto3 here.

### 7.2 Lambda + Function URLs

| Helper | Methods we use |
|--------|-----------------|
| `osbot_aws.aws.lambda_.Lambda` | `create`, `update`, `delete`, `exists`, `set_env_variable(s)`, `function_url_create_with_public_access`, `function_url_create`, `function_url_info`, `function_url_update`, `function_url_delete`, `permission_add` |
| `osbot_aws.deploy.Deploy_Lambda` | High-level: `add_folder`, `add_module`, `add_osbot_aws`, `add_osbot_utils`, `set_handler`, `set_container_image`, `set_env_variables`, `deploy`, `update`, `function_url`, `invoke`, `delete`. **This is the canonical Lambda deploy harness.** Phase 2b's `sg aws lambda` primitive is a thin Typer wrapper over it |
| `osbot_aws.helpers.Lambda_Package` | Lower-level zip + layer builder |
| `osbot_aws.aws.lambda_.Lambda__with_temp_role` | Convenience wrapper for the temp-IAM-role pattern |

### 7.3 IAM

`osbot_aws.aws.iam.IAM_Role_With_Policy` — the canonical "create a role + attach a policy" pattern. Used to mint the Waker Lambda's execution role.

### 7.4 SSM Parameter Store — the slug registry backing

`osbot_aws.helpers.Parameter`:
- `put(value, description='', type='String', overwrite=True)`, `get()`, `delete()`, `exists()`, `list()`
- `put_secret(value)`, `get_secret()`, `pull_secret()`

A single namespace `/sg-compute/vault-publish/<slug>/{instance-id,stack-name,billing-ref,...}` covers the entire registry. No DynamoDB needed for phase 1 / 2.

### 7.5 CloudFront — **THE GAP**

`osbot_aws.aws.cloud_front.Cloud_Front` exposes **only**:
- `distributions()` — list (no pagination; has a `# todo` comment)
- `invalidate_path(distribution_id, path)` / `invalidate_paths(...)` — cache invalidation

**No create / update / delete of distributions. No origin config helpers. No alternate-name management. No cert wiring.** Phase 2a fills this in.

Precedent for this: `sg aws dns`'s `Route53__AWS__Client` notes the same gap for Route 53 and wraps boto3 directly with an "EXCEPTION — migrate to osbot-aws once the wrapper grows" header. We do the same for CloudFront in `sg aws cf`.

### 7.6 ECS / Fargate — phase 3 target

| Helper | What it covers |
|--------|----------------|
| `osbot_aws.aws.ecs.ECS` | Cluster / service management |
| `osbot_aws.aws.ecs.ECS_Cluster` | Cluster-bound helper |
| `osbot_aws.aws.ecs.ECS_Fargate_Task` | Per-task helper — `start`, `stop`, `info`, ENI / private-IP lookup |
| `osbot_aws.aws.ecs.Temp_ECS_Fargate_Task` | Test helper |

These mean phase 3 (`Endpoint__Resolver__Fargate`) is a swap-in. The Waker handler stays the same.

### 7.7 Route 53 / ACM in osbot-aws

`osbot_aws.aws.route_53.{Route_53, Route_53__Hosted_Zone}` and `osbot_aws.apis.ACM` exist but are **not** the same surface as `sg aws dns`'s `Route53__AWS__Client`. The repo's wrapper covers things osbot-aws does not (paginated lists, the change-batch upsert shape, alias-target binding). The Waker should use the repo's `Route53__AWS__Client` directly — same boto3 boundary, same TODO migration note.

---

## 8. `osbot-utils` — primitives we will lean on

`osbot_utils.type_safe.Type_Safe` — base class for everything we write. CLAUDE.md rule #1.

`osbot_utils.type_safe.primitives.core.Safe_Str` + `Safe_Int` — base for every primitive in the spec. `Enum__Safe_Str__Regex_Mode` controls MATCH (strict) vs REPLACE (sanitise).

`osbot_utils.type_safe.type_safe_core.collections.{Type_Safe__List, Type_Safe__Dict}` — typed collections (CLAUDE.md rule #2 forbids raw `list` / `dict` attributes).

`osbot_utils.type_safe.type_safe_core.decorators.type_safe.type_safe` — decorator for runtime arg-type checking on method calls.

The vault-publish spec uses these everywhere; nothing new on the type-safety side.

---

## 9. What does NOT exist (and what the new work must add)

| Missing | Where it lands | Section |
|---------|----------------|---------|
| `sg vault-app stop` / `start` verbs | `sg_compute_specs/vault_app/` (additions) | [`03 §3`](03__sg-compute-additions.md#3-extend-sg-vault-app-with-stop-and-start) |
| Re-run auto-DNS on `start` | `Vault_App__Service.start_stack` | [`03 §3`](03__sg-compute-additions.md#3-extend-sg-vault-app-with-stop-and-start) |
| IMDSv2 → STS → EC2 self-stop hook | `Vault_App__User_Data__Builder` (small addition) | [`03 §3`](03__sg-compute-additions.md#3-extend-sg-vault-app-with-stop-and-start) |
| IAM policy: `ec2:StopInstances` on the EC2 instance profile | `playwright-ec2` profile | [`03 §3.4`](03__sg-compute-additions.md#34-iam-policy-addition) |
| `sg aws cf` primitive | `sgraph_ai_service_playwright__cli/aws/cf/` (new subpackage) | [`03 §4`](03__sg-compute-additions.md#4-sg-aws-cf-cloudfront-primitive) |
| `sg aws lambda` primitive | `sgraph_ai_service_playwright__cli/aws/lambda_/` (new subpackage) | [`03 §5`](03__sg-compute-additions.md#5-sg-aws-lambda-primitive) |
| The vault-publish spec | `sg_compute_specs/vault_publish/` (new spec) | [`04`](04__vault-publish-spec.md) |
| Waker Lambda handler | `sg_compute_specs/vault_publish/waker/` | [`04 §5`](04__vault-publish-spec.md#5-the-waker-lambda-handler) |
| Wildcard cert + wildcard A-alias (one-time bootstrap) | manual (or `sg vault-publish bootstrap`) | [`04 §6`](04__vault-publish-spec.md#6-the-bootstrap-flow) |

That is the complete net-new work. Everything else is reuse.
