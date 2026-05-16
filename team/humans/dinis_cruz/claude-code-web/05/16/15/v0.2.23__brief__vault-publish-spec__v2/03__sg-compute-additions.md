---
title: "03 — SG/Compute additions (outside the spec)"
file: 03__sg-compute-additions.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 03 — SG/Compute additions (outside the spec)

What we add to the SG/Compute platform **outside** `sg_compute_specs/vault_publish/`, because these are general-purpose primitives that other specs will reuse.

Three additions: small extension to the existing `sg vault-app` spec, two new AWS primitives (`sg aws cf`, `sg aws lambda`). All three follow the precedent set by `sg aws dns`.

---

## 1. Why these are not in the spec

The vault-publish spec is **glue** — it knows about slugs, about a per-slug A record, about an SSM-Parameter-Store registry, about kicking off a vault-app stack. It does not know how to manage a CloudFront distribution or deploy a Lambda. Those are reusable platform capabilities; the next spec that wants subdomain-routed compute (or wants a deploy-anything Lambda) gets to skip building them.

Treat these as **co-arriving infrastructure**. They land alongside the spec; phase 2 is "the spec + its two new platform primitives". After phase 2 they live on their own.

---

## 2. The pattern every addition follows

Mirror the `sg aws dns` shape exactly (see [`02 §2`](02__what-exists-today.md#2-this-repo--sg-aws-dns-the-dns-layer)):

- Own subpackage under `sgraph_ai_service_playwright__cli/aws/<service>/`
- `cli/Cli__<Service>.py` with sub-typer groups
- `service/<Service>__AWS__Client.py` — **sole boto3 boundary**, module header lists the "EXCEPTION — migrate to osbot-aws once the wrapper covers X" rationale
- `service/<Service>__<Topic>.py` for any non-trivial logic (e.g. config builders, verifiers)
- `schemas/Schema__<Service>__<Thing>.py` — Type_Safe data classes
- `enums/Enum__<Service>__<Thing>.py` — closed-set values
- `primitives/Safe_Str__<Service>__<Thing>.py` — typed strings (IDs, names, ARNs)
- `collections/List__Schema__<Service>__<Thing>.py` — typed lists
- Mutations gated by env var: `SG_AWS__<SERVICE>__ALLOW_MUTATIONS=1` (matches `SG_AWS__DNS__ALLOW_MUTATIONS=1` in `Cli__Dns.py:117`)
- Tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/<service>/`; in-memory client subclass for no-mocks composition

---

## 3. Extend `sg vault-app` with `stop` and `start`

The single missing piece in the existing vault-app spec. Small change: ~3 service methods, 2 schemas, 2 CLI verbs, a small user-data hook, one IAM policy line.

### 3.1 New verbs

| Verb | Behaviour |
|------|-----------|
| `sg vault-app stop <name>` | EC2 stops (not terminates); per-slug A record gets deleted so the wildcard takes over for the slug |
| `sg vault-app start <name>` | EC2 starts; on `running` state + `status-ok`, auto-DNS re-runs (writes new public IP to the per-slug A record); vault data persists on the root EBS volume |

### 3.2 Service methods

```python
# sg_compute_specs/vault_app/service/Vault_App__Service.py  (additions)

def stop_stack(self, region: str, name: str) -> Schema__Vault_App__Stop__Response:
    details = self.aws_client.instance.find_by_stack_name(region, name)
    if details is None:
        raise ValueError(f'No vault-app stack found with name {name!r}')
    iid = details.get('InstanceId', '')
    self.aws_client.ec2.instance_stop(iid)                            # osbot_aws.EC2.instance_stop
    self.aws_client.ec2.wait_for_instance_stopped(iid)                # osbot_aws.EC2.wait_for_instance_stopped
    # Tear down the per-slug A record so the wildcard takes over while the box is stopped.
    self._delete_per_slug_a_record(name, details)
    return Schema__Vault_App__Stop__Response(...)

def start_stack(self, region: str, name: str) -> Schema__Vault_App__Start__Response:
    details = self.aws_client.instance.find_by_stack_name(region, name)
    if details is None:
        raise ValueError(f'No vault-app stack found with name {name!r}')
    iid = details.get('InstanceId', '')
    self.aws_client.ec2.instance_start(iid)                           # osbot_aws.EC2.instance_start
    self.aws_client.ec2.wait_for_instance_running(iid)                # osbot_aws.EC2.wait_for_instance_running
    self.aws_client.ec2.wait_for_instance_status_ok(iid)              # status checks (3/3) — ~60-90s
    # Re-fetch — the public IP almost certainly changed
    details_fresh = self.aws_client.instance.find_by_stack_name(region, name)
    public_ip     = details_fresh.get('PublicIpAddress', '')
    tls_hostname  = self._tls_hostname_from_tags(details_fresh)       # the per-slug FQDN tag set at create
    if tls_hostname and public_ip:
        # Re-write the per-slug A record so traffic goes direct again
        Vault_App__Auto_DNS().run(tls_hostname, public_ip)
    return Schema__Vault_App__Start__Response(...)
```

`_delete_per_slug_a_record` uses `Route53__AWS__Client.delete_record(...)` from the existing `sg aws dns` service classes.

### 3.3 The "stop on idle instead of terminate" change

Today's auto-terminate timer (`systemd-run --on-active=Nh /sbin/shutdown -h now`) terminates the instance. For vault-publish we want the instance to **stop itself** so vault-publish can `start` it back.

Change in `Vault_App__User_Data__Builder.render(...)`:

```bash
# OLD: shutdown -h now  (which → terminate, because the instance is shutdown-terminate by default)
# NEW: aws ec2 stop-instances --instance-ids $(curl -s ...meta-data.../instance-id)
```

The instance reads its own ID from IMDSv2, uses its instance-profile credentials, calls `ec2:StopInstances` on itself. This is the proven pattern from `sg lc extend` (`sg_compute_specs/local_claude/`).

Two preconditions:

- The instance profile (`playwright-ec2`) needs `ec2:StopInstances` on `arn:aws:ec2:*:*:instance/*` with a condition `aws:ResourceTag/StackType=vault-app` so an instance can only stop instances of its own kind, including itself. See §3.4.
- The launch config needs `InstanceInitiatedShutdownBehavior=stop` (not the default `terminate`). This is a single boto3 launch-template field; goes in `Vault_App__AWS__Client.launch.run_instance(...)`.

### 3.4 IAM policy addition

The shared `playwright-ec2` instance profile is configured under `sgraph_ai_service_playwright__cli/deploy/` (see `SP__CLI__Lambda__Policy.py` precedent — the same shape applies to EC2 profile policy).

Add (or amend the existing inline policy):

```json
{
  "Effect"  : "Allow",
  "Action"  : ["ec2:StopInstances"],
  "Resource": "arn:aws:ec2:*:*:instance/*",
  "Condition": {
    "StringEquals": {"aws:ResourceTag/StackType": "vault-app"}
  }
}
```

Once-only policy change. Tracked as a phase-1a sub-task.

### 3.5 New schemas

| Schema | Fields |
|--------|--------|
| `Schema__Vault_App__Stop__Request`  | `region: str = ''`, `name: str = ''` |
| `Schema__Vault_App__Stop__Response` | `name: str`, `instance_id: str`, `stopped: bool`, `dns_record_deleted: bool`, `elapsed_ms: int` |
| `Schema__Vault_App__Start__Request` | `region: str = ''`, `name: str = ''` |
| `Schema__Vault_App__Start__Response`| `name: str`, `instance_id: str`, `public_ip: str`, `tls_hostname: str`, `dns_record_updated: bool`, `elapsed_ms: int` |

All in `sg_compute_specs/vault_app/schemas/`.

### 3.6 Test plan

Compose `Vault_App__AWS__Client__In_Memory` (extending the existing one in `vault_app/tests/`) with the EC2 lifecycle methods stubbed to flip in-memory state. No mocks. Tests cover:

- `stop`: stopped → instance state stopped → A record deleted
- `stop`: instance not found → `ValueError`
- `start`: stopped → running → status-ok → A record upserted to new IP
- `start`: instance already running → idempotent (no-op DNS update if IP unchanged)
- DNS failure path: stop / start return the Auto_DNS result with `error` populated; service does not raise

---

## 4. `sg aws cf` — CloudFront primitive

The largest new piece in this brief — fills the `osbot_aws.aws.cloud_front.Cloud_Front` gap (which today only does `list` + `invalidate`).

### 4.1 CLI surface

```
sg aws cf
├── distributions
│     list                       — list distributions in the account
│     ids                        — just the ids (scripting)
├── distribution
│     show <id>                  — full config
│     status <id>                — Deployed / InProgress
│     create  --origin-fn-url <url> --aliases '*.sg-compute.sgraph.ai' --cert-arn arn:...
│     update  <id> [--add-alias / --remove-alias / --add-origin / --primary-origin <id>]
│     disable <id>               — flip Enabled=false (precondition for delete)
│     delete  <id>               — only after disable + Deployed
├── origins
│     list <id>                  — origins of a distribution
│     add  <id> --type lambda-function-url --url <url> [--connection-timeout 2]
│     remove <id> --origin-id <oid>
└── invalidations
      create <id> --path '/'     — already covered by osbot_aws; thin pass-through
      list   <id>
```

Mutations require `SG_AWS__CF__ALLOW_MUTATIONS=1`.

### 4.2 Service classes

| Class | Responsibility |
|-------|----------------|
| `CloudFront__AWS__Client` | Sole boto3 boundary. Methods: `list_distributions` (paginated), `get_distribution`, `get_distribution_config`, `create_distribution`, `update_distribution`, `disable_distribution`, `delete_distribution`, `wait_for_deployed`. Header note: "EXCEPTION — `osbot_aws.Cloud_Front` only covers list + invalidate; migrate once distribution-management lands there." |
| `CloudFront__Distribution__Builder` | Type_Safe builder for `DistributionConfig` payloads. Knows: alternate domain names, default cache behaviour (forward Host header, low TTL), origin groups (primary + secondary for failover), ACM cert ARN wiring, default root object. Pure data — no boto3 |
| `CloudFront__Origin__Failover__Builder` | Specific builder for the origin-failover config (primary origin + secondary origin + criteria status codes). The vault-publish bootstrap uses this once: primary = Lambda Function URL, no secondary in phase 2; secondary added in phase 4 when ALB lands |

### 4.3 Schemas

| Schema | Fields (sketch) |
|--------|------------------|
| `Schema__CF__Distribution` | `distribution_id`, `domain_name`, `status`, `enabled`, `aliases`, `origins`, `default_cache_behavior`, `cert_arn`, `caller_reference`, `last_modified` |
| `Schema__CF__Origin` | `origin_id`, `domain_name`, `origin_type` (`Enum__CF__Origin__Type` = `s3` / `custom` / `lambda-function-url`), `path_pattern`, `custom_origin_config` |
| `Schema__CF__Distribution__Create__Request` | `aliases: List__Safe_Str__Domain_Name`, `primary_origin_url: str`, `cert_arn: str`, `comment: str` |
| `Schema__CF__Distribution__Create__Response` | `distribution_id`, `domain_name` (the `dxxx.cloudfront.net` to ALIAS at), `status`, `caller_reference`, `elapsed_ms` |
| `Schema__CF__Update__Result` | `distribution_id`, `etag_before`, `etag_after`, `status` |

### 4.4 Enums

| Enum | Values |
|------|--------|
| `Enum__CF__Origin__Type` | `S3` / `CUSTOM` / `LAMBDA_FUNCTION_URL` |
| `Enum__CF__Distribution__Status` | `DEPLOYED` / `IN_PROGRESS` |
| `Enum__CF__Cache__Policy__Preset` | `NO_CACHE` (forward Host, TTL 0) / `STANDARD` (TTL 86400) — small preset set rather than full cache-policy modelling |

### 4.5 Primitives

| Primitive | What it constrains |
|-----------|---------------------|
| `Safe_Str__CF__Distribution_Id` | `Exxx...` (uppercase alphanumeric, ~14 chars) |
| `Safe_Str__CF__Domain_Name` | `dxxx.cloudfront.net` — the auto-generated CF domain |
| `Safe_Str__CF__Caller_Reference` | UUID-ish — required-unique per CreateDistribution call |
| `Safe_Str__CF__ARN` | `arn:aws:cloudfront::...:distribution/Exxx` |

### 4.6 Test approach

`CloudFront__AWS__Client__In_Memory` subclass with an in-memory dict of distributions. Tests cover:

- create → list shows it
- create with origin-failover config → readback shows both origins
- update + add alias → readback shows it
- disable → status flips
- delete on enabled distribution → error
- delete on disabled + Deployed → success
- `wait_for_deployed`: polls `get_distribution`, returns when status=='Deployed' or timeout

### 4.7 File count estimate

- 1 CLI file (`Cli__Cf.py`, ~600 lines like `Cli__Dns.py`)
- 3 service files (`CloudFront__AWS__Client`, `Distribution__Builder`, `Origin__Failover__Builder`)
- 5-6 schemas
- 3 enums
- 4 primitives
- 2 collections
- ~6 test files

**Total ~24 files.** The biggest single piece in the whole brief.

---

## 5. `sg aws lambda` primitive

Thin Typer wrapper over `osbot_aws.deploy.Deploy_Lambda` (see [`02 §7.2`](02__what-exists-today.md#72-lambda--function-urls)).

### 5.1 CLI surface

```
sg aws lambda
├── deployments
│     list                       — list functions in the region
├── deployment
│     show <name>                — full function info + URL if any
│     deploy <name> --code-path <path> --handler <module:func>
│                   [--env KEY=val ...] [--memory 512] [--timeout 30]
│                   [--add-osbot-utils] [--add-osbot-aws]
│                   [--container-image <uri>]
│     update <name> [--code-path <path>] [--env KEY=val ...] [--memory] [--timeout]
│     delete <name>
├── url
│     create <name> [--auth-type AWS_IAM | NONE]
│     show <name>
│     delete <name>
├── invoke <name> --payload '{...}' | --payload-file <path>
└── logs <name> [--tail 100] [--follow]
```

Mutations require `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1`.

### 5.2 Service classes

Most of the work is already in `Deploy_Lambda`. The new service classes are thin:

| Class | Responsibility |
|-------|----------------|
| `Lambda__Deployer` | Type_Safe wrapper over `Deploy_Lambda`. Translates `Schema__Lambda__Deploy__Request` → `Deploy_Lambda.set_*(...)`. Returns `Schema__Lambda__Deploy__Response` |
| `Lambda__AWS__Client` | Thin convenience wrapper over `osbot_aws.aws.lambda_.Lambda` for the list / show / invoke / logs paths. Sole boto3 boundary for the read paths |
| `Lambda__Url__Manager` | Wraps `Lambda.function_url_*` for the URL sub-commands |

We do **not** wrap `Deploy_Lambda` underneath; we use it directly inside `Lambda__Deployer`. Lambda packaging is its problem.

### 5.3 Schemas

| Schema | Fields |
|--------|--------|
| `Schema__Lambda__Deploy__Request` | `name`, `code_path: str`, `handler: str`, `runtime: str = 'python3.12'`, `memory: int = 512`, `timeout: int = 30`, `env: Dict__Str__Str`, `add_osbot_utils: bool`, `add_osbot_aws: bool`, `container_image_uri: str` |
| `Schema__Lambda__Deploy__Response` | `function_name`, `function_arn`, `function_url: str`, `code_size_bytes: int`, `elapsed_ms` |
| `Schema__Lambda__Function__Info` | full read-side info |
| `Schema__Lambda__Url__Info` | `url`, `auth_type`, `invoke_mode` |
| `Schema__Lambda__Invoke__Result` | `status_code`, `payload`, `executed_version`, `function_error` |

### 5.4 File count estimate

- 1 CLI file (~300 lines — `Deploy_Lambda` does the heavy lifting)
- 3 service files
- 5 schemas
- 2 enums
- 3 primitives (`Safe_Str__Lambda__Name`, `Safe_Str__Lambda__ARN`, `Safe_Str__Lambda__Url`)
- 2 collections
- ~5 test files

**Total ~16 files.** Half the size of `sg aws cf`.

---

## 6. Cross-cutting — env vars and conventions

| Env var | Default | Used by |
|---------|---------|---------|
| `SG_AWS__DNS__DEFAULT_ZONE` | `sg-compute.sgraph.ai` | `Route53__AWS__Client` (existing); the vault-publish spec reads the same |
| `SG_AWS__DNS__ALLOW_MUTATIONS` | unset | `Cli__Dns` mutations (existing) |
| `SG_AWS__CF__ALLOW_MUTATIONS` | unset | `Cli__Cf` mutations (new) |
| `SG_AWS__LAMBDA__ALLOW_MUTATIONS` | unset | `Cli__Lambda` mutations (new) |
| `SG_AWS__CF__DEFAULT_DISTRIBUTION_ID` | unset | The vault-publish spec uses this to find the bootstrap distribution. Set by `sg vault-publish bootstrap` and pinned in a config file |
| `SG_AWS__LAMBDA__WAKER_FUNCTION_NAME` | `sg-vault-publish-waker` | The vault-publish spec / Waker. Set at bootstrap |

---

## 7. Things explicitly NOT in scope of these additions

- **`sg aws acm request`** — issuing the wildcard cert is a one-time manual step in phase 2; the ACM ARN is pinned as config. Adding `request-certificate` to the existing `sg aws acm` is a small follow-up but not required by this brief.
- **`sg aws ec2`** as a CLI primitive — the EC2 surface already gets exercised through the various stack specs (`sg elastic`, `sg vault-app`, etc.). No need to expose a raw `sg aws ec2` today.
- **CloudFront Functions / Lambda@Edge** — the Waker is a regional Lambda invoked by a Function URL set as the CloudFront origin. CloudFront Functions and Lambda@Edge add cold-start optimisations but are out of scope.
- **Multi-region** — single `us-east-1` cert + one CloudFront distribution. Region failover is phase 5 territory.

---

## 8. Boundary clarification — who owns what

| Capability | Owner | Reason |
|------------|-------|--------|
| Slug naming / reserved list / validation | `sg_compute_specs/vault_publish/` | Spec-specific; not a platform primitive |
| Slug registry (SSM Parameter Store namespace) | `sg_compute_specs/vault_publish/` | Spec-specific schema |
| Waker Lambda handler code | `sg_compute_specs/vault_publish/` | Spec-specific routing logic |
| Stop / start an EC2 stack | `sg_compute_specs/vault_app/` | General to vault-app, not specific to publishing |
| Per-slug A record on start | `sg_compute_specs/vault_app/` (via `Vault_App__Auto_DNS` — already exists) | Already auto-runs at create; just extend to start |
| Per-slug A record delete on stop | `sg_compute_specs/vault_app/` | Symmetric with `Auto_DNS.run` on create / start |
| CloudFront distribution lifecycle | `sg aws cf` | Reusable platform primitive |
| Lambda deploy + URL | `sg aws lambda` | Reusable platform primitive |
| Route 53 record mutations | `sg aws dns` (existing) | Already there |
| ACM cert (one-time bootstrap) | manual + `sg aws acm` (read) | Out of scope to extend ACM right now |

This division means: when the next spec ("publish a vault-app stack at `<slug>.something-else.sgraph.ai`" or "publish a Fargate task at `<slug>.fargate-app.sgraph.ai`") comes along, it picks up `sg aws cf` + `sg aws lambda` + `sg aws dns` for free and only writes its own slug-routing logic.
