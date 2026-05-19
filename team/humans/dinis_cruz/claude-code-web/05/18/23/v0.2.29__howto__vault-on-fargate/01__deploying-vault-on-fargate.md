---
title: Deploying the SG vault to AWS Fargate using `sg aws fargate`
status: how-to / gap-analysis
audience: dinis_cruz
author: claude-opus-4-7
date: 2026-05-18
related:
  - sgraph_ai_service_playwright__cli/aws/fargate/cli/Cli__Fargate.py
  - sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py
  - sg_compute_specs/vault_app/cli/Cli__Vault_App.py
  - sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py
  - sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py
---

# Deploying the SG vault to AWS Fargate

## TL;DR

You can get the vault container **running on Fargate today** with the existing
`sg aws fargate` commands, but you **cannot reach the end-state of `sg vault-app create`**
without either (a) doing several things out-of-band (IAM role, log group, port
mappings hand-edited via the boto3 client, ALB, DNS) or (b) extending
`sg aws fargate` with the few capabilities listed under [Gaps](#gaps-that-block-a-one-shot-deploy).

The fastest path to a working vault-on-Fargate today:

1. Out-of-band: ECS task execution role, CloudWatch log group, VPC + subnets +
   security group, ALB with target group (because we have no port mappings yet).
2. `sg aws fargate cluster create vault`
3. Register a task definition (currently no port-mapping flag — see workaround).
4. `sg aws fargate task run --cluster vault --task-def vault:1 --subnet ... --sg ... --assign-public-ip`
5. Manually create the Route 53 record.

This document explains exactly what is and isn't possible, what the vault
container needs, and what's missing from `sg aws fargate` to close the gap with
`sg vault-app`.

---

## What `sg vault-app create` does today (for context)

`sg vault-app create` deploys the vault as a **Docker container on an EC2
instance**, not on Fargate. The orchestration is:

| Step | What happens | Where |
|------|--------------|-------|
| 1. Resolve AMI | Latest AL2023 | `Vault_App__AWS__Client.EC2__AMI__Helper` |
| 2. Ensure SG | `:8080` to caller IP, `:80/:443` world-open if TLS | `EC2__SG__Helper` |
| 3. Build user-data | cloud-init that writes `/opt/vault-app/docker-compose.yml` and runs `compose up -d` | `Vault_App__User_Data__Builder` + `Vault_App__Compose__Template` |
| 4. Launch instance | t3.medium spot, EBS 20 GiB, `playwright-ec2` instance profile, TerminateAt tag | `EC2__Launch__Helper.run_instance` |
| 5. (optional) DNS | Parallel thread creates Route 53 A record under `sg-compute.sgraph.ai` | `Vault_App__Auto_DNS` |
| 6. Wait / health | Polls `http://<ip>:8080/info/health` (or `https://<ip>:443/info/health` with `--with-tls-check`) | `Spec__CLI__Builder` |

The vault container itself is `diniscruz/sg-send-vault:latest` (Docker Hub),
consuming these env vars:

```
SGRAPH_SEND__ACCESS_TOKEN        # shared secret — vault API key
SEND__STORAGE_MODE               # disk | memory | s3
SG_VAULT_APP__SEED_VAULT_KEYS    # comma-separated sgit keys to pre-load
FAST_API__TLS__ENABLED           # true when --with-tls-check
FAST_API__TLS__CERT_FILE         # /certs/cert.pem (volume-mounted)
FAST_API__TLS__KEY_FILE          # /certs/key.pem  (volume-mounted)
```

Ports the container exposes:

| Port | Purpose | Public? |
|------|---------|---------|
| `8080` | HTTP API + `/info/health` | bound to caller IP /32 only |
| `443`  | HTTPS API (when TLS enabled) | world-open (token-gated) |
| `80`   | Lets-Encrypt http-01 challenge | world-open, transient |

Persistent state lives in `/data` inside the container, bind-mounted to
`/opt/vault-app/data` on the EC2 root volume.

---

## What `sg aws fargate` gives us today

Source: `sgraph_ai_service_playwright__cli/aws/fargate/cli/Cli__Fargate.py`

```
sg aws fargate cluster list                                  [--json]
sg aws fargate cluster describe <name>                       [--json]
sg aws fargate cluster create   <name>  [--tag k=v]          [--yes]
sg aws fargate cluster delete   <name>                       [--yes]

sg aws fargate task-def list                  [--family F]   [--json]
sg aws fargate task-def show     <fam:rev>                   [--json]
sg aws fargate task-def register --name N --image IMG
                                [--cpu 256] [--memory 512]
                                [--env k=v]...               [--yes]

sg aws fargate task list         [--cluster C] [--family F]  [--json]
sg aws fargate task describe <arn> [--cluster C]             [--json]
sg aws fargate task run    --cluster C --task-def F:R
                           [--count 1] [--subnet S]... [--sg G]...
                           [--assign-public-ip]              [--yes]
sg aws fargate task stop    <arn>  [--cluster C] [--reason R] [--yes]
sg aws fargate task logs    <arn>  [--cluster C] [--since 30m] [--json]
```

All mutations are gated on `SG_AWS__FARGATE__ALLOW_MUTATIONS=1`.

---

## End-to-end "vault on Fargate" walk-through

### 0. Prerequisites (all out-of-band — `sg aws fargate` does NOT help here)

```bash
export AWS_REGION=eu-west-2
export SG_AWS__FARGATE__ALLOW_MUTATIONS=1
```

#### 0a. Push the vault image to ECR (recommended) OR allow Docker Hub pulls

Fargate can pull from Docker Hub, but anonymous pulls are rate-limited and
won't work reliably without authentication. Two options:

**Option A — mirror to ECR (recommended):**

```bash
# Create the ECR repo (the new sg aws ecr surface from this branch):
sg aws ecr repo-create sg-send-vault                        # SG_AWS__ECR__ALLOW_MUTATIONS=1

# Tag + push (assumes you have the image locally):
ECR_HOST=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION}.amazonaws.com
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_HOST
docker pull diniscruz/sg-send-vault:latest
docker tag  diniscruz/sg-send-vault:latest $ECR_HOST/sg-send-vault:latest
docker push $ECR_HOST/sg-send-vault:latest
```

**Option B — Docker Hub credentials via Secrets Manager:**

Create a Secrets Manager secret with your Docker Hub username/password and
reference it via `repositoryCredentials` in the task definition. **This is not
expressible through `sg aws fargate task-def register` today** — see [Gaps](#gaps).

#### 0b. Create the ECS task execution role

```bash
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

This role is required by `register_task_definition`. **`sg aws fargate` does
not currently let you set this on the task definition** (the field is
hard-coded to empty at `Fargate__AWS__Client.register_task_definition` line
144). See [Gaps](#gaps).

#### 0c. Create the CloudWatch log group

`Fargate__AWS__Client.register_task_definition` uses log group `/ecs/<family>`
but does not create it. Pre-create:

```bash
aws logs create-log-group --log-group-name /ecs/vault
aws logs put-retention-policy --log-group-name /ecs/vault --retention-in-days 7
```

#### 0d. Identify VPC + subnets + security group

`sg aws fargate task run` requires subnet and SG IDs — there is no default
lookup. Use the new `sg aws ec2 sg` surface from this branch to find or create
candidates:

```bash
# Find security groups in a given VPC:
sg aws ec2 sg list --vpc vpc-0abc123
# Use whichever SG opens :443 + :80 + :8080 outbound,
# and :443/:80/:8080 inbound from your callers (or your ALB).

# Find your subnets (no first-class CLI yet — use awscli):
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-0abc123 \
  --query 'Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]' --output table
```

#### 0e. Generate vault access token

```bash
ACCESS_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
echo "$ACCESS_TOKEN"                             # save it — you need this to call the vault
```

### 1. Create the Fargate cluster

```bash
sg aws fargate cluster create vault --tag purpose=vault --tag owner=dinis --yes
sg aws fargate cluster describe vault
```

This creates an ECS cluster with `FARGATE + FARGATE_SPOT` capacity providers
and Container Insights enabled
(`Fargate__AWS__Client.create_cluster` lines 79–92).

### 2. Register the vault task definition

```bash
sg aws fargate task-def register \
  --name vault \
  --image $ECR_HOST/sg-send-vault:latest \
  --cpu 512 \
  --memory 1024 \
  --env SGRAPH_SEND__ACCESS_TOKEN=$ACCESS_TOKEN \
  --env SEND__STORAGE_MODE=memory \
  --yes
```

**Important caveats:**

- **No port mappings.** The task definition will register but the container
  port `8080` will not be advertised. The task will start, the container will
  listen on `8080` inside its namespace, but **nothing outside the task can
  reach it** without port mappings.

  **Workaround until the CLI grows `--port-mapping`:** use the boto3 client
  directly or amend the JSON via the AWS console after registration. Or, hand
  off the `register_task_definition` call to a short ad-hoc Python script that
  reuses `Fargate__AWS__Client.client()` and adds:
  ```python
  containerDefinitions=[{
      'name': 'vault',
      'image': image,
      'essential': True,
      'portMappings': [{'containerPort': 8080, 'protocol': 'tcp'},
                       {'containerPort': 443,  'protocol': 'tcp'}],
      'environment': [...],
      'logConfiguration': {...},
  }]
  ```

- **No `executionRoleArn`.** Without it, image pulls from ECR and log writes
  to CloudWatch will fail. Same workaround applies.

- **No `taskRoleArn`.** Means the task itself cannot AssumeRole anything — so
  `SEND__STORAGE_MODE=s3` will not work without it. Pick `memory` or `disk`
  unless you patch the task definition.

- **`--memory` 1024 / `--cpu` 512 sizing** matches what t3.medium gives the
  vault today (2 vCPU shared, 4 GiB). Bump to `--cpu 1024 --memory 2048` for
  parity with playwright-mode.

### 3. Run the task

```bash
sg aws fargate task run \
  --cluster vault \
  --task-def vault:1 \
  --count 1 \
  --subnet subnet-0xxx --subnet subnet-0yyy \
  --sg     sg-0zzz \
  --assign-public-ip \
  --yes
```

Capture the task ARN from the output.

### 4. Wait, check, log

```bash
sg aws fargate task list --cluster vault                                # confirm RUNNING
sg aws fargate task describe arn:aws:ecs:eu-west-2:...:task/vault/xxx --cluster vault
sg aws fargate task logs     arn:aws:ecs:eu-west-2:...:task/vault/xxx --cluster vault --since 5m
```

`task describe` includes the attachment ENI; resolve it to the public IP via
the new `sg aws ec2 sg` / `aws ec2 describe-network-interfaces` to learn where
to hit the vault.

### 5. DNS (manual)

```bash
# Pull the ENI ID out of the task description, then:
ENI=eni-0aaa
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

aws route53 change-resource-record-sets --hosted-zone-id Z01234567 --change-batch '{
  "Changes":[{"Action":"UPSERT","ResourceRecordSet":{
    "Name":"vault-fargate.sg-compute.sgraph.ai.","Type":"A","TTL":60,
    "ResourceRecords":[{"Value":"'$PUBLIC_IP'"}]}}]}'
```

There is no `sg aws fargate` equivalent of `--with-aws-dns` yet.

### 6. Health check

```bash
curl http://$PUBLIC_IP:8080/info/health     # only works once port-mapping is in the task definition
```

### 7. Teardown

```bash
sg aws fargate task stop <task-arn>  --cluster vault --reason "done" --yes
sg aws fargate cluster delete vault --yes
```

---

## Gaps that block a one-shot deploy

These are the **real** blockers — items 1–4 will turn the above 0-step
prerequisite list into the 1-step `sg aws fargate` invocation users expect.

| # | Gap | Where | Impact |
|---|-----|-------|--------|
| 1 | **No `--port-mapping` on `task-def register`** | `Fargate__AWS__Client.register_task_definition` (`containerDefinitions[0].portMappings` is never populated) | Container is unreachable. Must hand-patch the task def. |
| 2 | **No `--execution-role-arn` on `task-def register`** | Same method, field is hard-coded to `''` (line 144) | Image pulls + log writes fail. Must hand-patch. |
| 3 | **No `--task-role-arn` on `task-def register`** | Same method | Vault can't AssumeRole → no S3 storage mode, no Secrets Manager. |
| 4 | **No Secrets Manager / SSM Parameters integration** | No `--secret` flag, `containerDefinitions[*].secrets` never populated | Access token has to be passed plaintext via `--env`. Visible in console / `describe-task-definition`. |
| 5 | **No `service` sub-command** (only one-off tasks) | No `Cli__Fargate.service_*` handlers; client has no `CreateService` / `UpdateService` | No ALB wiring, no auto-restart on task crash, no rolling deploy. |
| 6 | **No log-group auto-create** | `register_task_definition` references `/ecs/<family>` but doesn't create it | Silent failure if you forget the `aws logs create-log-group` step. |
| 7 | **No EFS / EBS volume support** | `containerDefinitions[*].mountPoints` + `volumes` never populated | Vault `/data` is ephemeral — restart loses keys. Disqualifies disk-mode persistence. |
| 8 | **No multi-container (sidecar) task** | CLI is single-container-shaped | Can't reproduce playwright mode (vault + cert-init + host-plane + mitmproxy). |
| 9 | **`launchType` hard-coded to `FARGATE`** (line 217) | Spot capacity provider is on the cluster but cannot be selected per run | No way to get the 70 % spot discount that `sg vault-app --use-spot` defaults to. |
| 10 | **No subnet / SG auto-lookup** | User must pass `--subnet` / `--sg` every time | Easy to forget; no "use the default VPC" path. |
| 11 | **No auto-DNS** (`--with-aws-dns` equivalent) | No Route 53 integration in fargate package | Public IP changes every restart; need an out-of-band step or an ALB. |
| 12 | **`task run` task tagging is limited** to `sg:managed=true` (line 222) | No `--tag` pass-through | Hard to associate the task with a stack name / owner / TerminateAt timer. |

---

## What a `sg aws fargate vault-up` would look like (sketch — NOT implemented)

If we wanted parity with `sg vault-app create` on Fargate, the path is roughly:

1. Land items **1, 2, 3, 6** above as small additive flags on existing commands
   — these are the minimum to make the current `task-def register` + `task run`
   loop produce a reachable container.
2. Add a `service` subcommand (item 5) so the vault is a long-running ECS
   service behind an ALB, not a one-off task.
3. Add an EFS volume helper (item 7) so vault keys survive a restart.
4. Build a new orchestrator at
   `sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__Vault__Deployer.py`
   that composes those primitives plus the ALB + Route 53 wiring (mirrors
   `Vault_App__Service.create_stack`).
5. Expose it as `sg aws fargate vault-up [--with-tls-check] [--with-aws-dns]
   [--storage-mode memory|efs] [--access-token T] [--seed-vault-keys K]`.

Items 8, 9, 11 are nice-to-haves; items 4 (Secrets Manager), 7 (EFS), 10
(subnet lookup) are real correctness/UX wins.

---

## Cost comparison (rough, eu-west-2, May 2026)

| Variant | Compute | Hour |
|---------|--------:|-----:|
| `sg vault-app` t3.medium spot       | t3.medium 2 vCPU / 4 GiB | ~$0.014 |
| `sg vault-app` t3.medium on-demand  | t3.medium 2 vCPU / 4 GiB | ~$0.046 |
| Fargate 0.5 vCPU / 1 GiB            | Fargate                   | ~$0.025 |
| Fargate 1 vCPU / 2 GiB              | Fargate                   | ~$0.049 |
| Fargate Spot 1 vCPU / 2 GiB         | Fargate Spot              | ~$0.015 |

For the auto-terminating dev usage `sg vault-app` is built around (`--max-hours
1`), EC2-spot is the cheaper path. Fargate becomes interesting as a
long-running production deploy (item 5 above), not as a replacement for
`sg vault-app create`'s short-lived per-developer stacks.

---

## Summary

- `sg aws fargate` is a **clean primitive surface** for clusters + task
  definitions + one-off tasks + logs. It is **not** a vault deployer.
- To deploy the vault on Fargate today you can: create a cluster, register a
  task definition with image + env vars + CPU/memory, run a task with subnet
  and SG flags, fetch its public IP, and call `/info/health`.
- You **cannot** today: wire up port mappings, attach an execution/task role,
  attach a secret, attach a volume, run as a service behind an ALB, or set up
  DNS — all through the CLI alone.
- Four small additive flags (`--port-mapping`, `--execution-role-arn`,
  `--task-role-arn`, `--secret`) close ~80 % of the gap. A `service`
  subcommand + EFS + an orchestrator class close the rest.
