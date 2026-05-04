# AWS Observability Stack — Console Setup Runbook

**Service:** SG Playwright EC2 stack  
**Date:** 2026-04-20  
**Scope:** One-time AWS console provisioning required before `sg-ec2 create` can ship data to AWS managed services.

---

## Architecture Overview

```
EC2 Instance
├── playwright           (core service)
├── agent-mitmproxy      (proxy sidecar)
├── cadvisor             ─┐
├── node-exporter        ─┤── scraped by Prometheus → remote_write → AMP
├── prometheus           ─┘
└── fluent-bit           ──────────────────────────────────────────→ OpenSearch

AMG (Managed Grafana) queries:
  ├── AMP          (metrics dashboards)
  ├── OpenSearch   (log search + dashboards)
  └── CloudWatch   (free EC2 hypervisor metrics — no agent needed)
```

---

## Step 1 — Amazon Managed Prometheus (AMP)

### 1.1 Create a workspace

1. Open **Amazon Managed Service for Prometheus** in the AWS Console.
2. Click **Create workspace**.
3. Set **Alias**: `sg-playwright` (optional, for display only).
4. Click **Create workspace**.

### 1.2 Note the remote write URL

After creation, open the workspace and copy:

- **Workspace ID** — looks like `ws-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Endpoint — remote write URL** — looks like:
  ```
  https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write
  ```

### 1.3 Set the environment variable

```bash
export AMP_REMOTE_WRITE_URL="https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write"
```

Add to your shell profile (`.zshrc` / `.bashrc`) or CI secrets.

### 1.4 IAM — already handled

`provision_ec2.py` attaches `AmazonPrometheusRemoteWriteAccess` to the `playwright-ec2` role automatically.  
Prometheus uses SigV4 auth via the EC2 instance role — no credentials embedded in config.

---

## Step 2 — Amazon OpenSearch Service

### 2.1 Create a domain

1. Open **Amazon OpenSearch Service** in the AWS Console.
2. Click **Create domain**.
3. **Deployment type**: Development and testing (for lower cost) or Production.
4. **Domain name**: `sg-playwright-logs`
5. **Engine version**: OpenSearch 2.x (latest stable)
6. **Instance type**: `t3.small.search` (2 nodes for HA, or 1 for dev)
7. **Network**: VPC is recommended; **Public access** is simpler for initial setup.
8. **Access policy**: Choose **Only use fine-grained access control**.
9. **Fine-grained access control**: Enable → create master user (save credentials).
10. Click **Create**.

> **Cost note**: `t3.small.search` × 1 node ≈ $0.036/hr (~$26/month). Use **UltraWarm** storage tier for older logs.

### 2.2 Note the endpoint

After the domain reaches **Active** status, copy:

- **Domain endpoint** — looks like:
  ```
  search-sg-playwright-logs-xxxxxx.eu-west-2.es.amazonaws.com
  ```
  (Just the hostname — no `https://` prefix)

### 2.3 Set the environment variable

```bash
export OPENSEARCH_ENDPOINT="search-sg-playwright-logs-xxxxxx.eu-west-2.es.amazonaws.com"
```

### 2.4 Grant the EC2 role access to the domain

Fluent Bit uses the EC2 instance role (`playwright-ec2`) for IAM auth. You need to map it inside OpenSearch.

**Option A — Resource-based domain access policy** (simpler):

In the domain → **Edit access policy**, add:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<ACCOUNT_ID>:role/playwright-ec2"
      },
      "Action": "es:*",
      "Resource": "arn:aws:es:<REGION>:<ACCOUNT_ID>:domain/sg-playwright-logs/*"
    }
  ]
}
```

Replace `<ACCOUNT_ID>` and `<REGION>`.

**Option B — Fine-grained access control** (recommended for production):

1. OpenSearch Dashboards → **Security** → **Roles** → `all_access` → **Mapped users**.
2. Add the IAM role ARN: `arn:aws:iam::<ACCOUNT_ID>:role/playwright-ec2`.

### 2.5 OpenSearch Serverless (alternative)

If you prefer **OpenSearch Serverless** (pay-per-use, no cluster management):

1. Open **OpenSearch Serverless** → **Create collection**.
2. Type: **Time series** (optimised for logs).
3. Name: `sg-playwright-logs`.
4. Create a **data access policy** granting the `playwright-ec2` role `aoss:CreateIndex`, `aoss:WriteDocument`, `aoss:UpdateIndex`.
5. In `provision_ec2.py`, set `AWS_Service_Name` to `aoss` instead of `es` in the Fluent Bit config (the `render_observability_configs_section` function has this as a comment).

> **Cost note**: ~$0.24/OCU/hr (min 2 OCUs for indexing + search = ~$0.48/hr). More expensive than a single `t3.small` node unless workloads are bursty.

---

## Step 3 — Amazon Managed Grafana (AMG)

### 3.1 Create a workspace

1. Open **Amazon Managed Grafana** in the AWS Console.
2. Click **Create workspace**.
3. **Workspace name**: `sg-playwright`
4. **Authentication**: AWS IAM Identity Center (SSO) — follow prompts to enable if needed.
5. **Permission type**: Service managed.
6. **Data sources**: Check **Amazon Managed Service for Prometheus**, **Amazon OpenSearch Service**, **Amazon CloudWatch**.
7. Click **Create workspace**.

### 3.2 Note the workspace URL

After creation, the workspace URL looks like:

```
https://g-xxxxxxxxxx.grafana-workspace.eu-west-2.amazonaws.com
```

### 3.3 Add users

In the workspace → **Authentication** → **AWS IAM Identity Center** → assign your user with **Admin** role.

### 3.4 Configure data sources inside Grafana

Open the Grafana workspace URL → **Configuration** → **Data sources**:

**Prometheus (→ AMP):**
- Type: Prometheus
- URL: `https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-xxxxx/`
- Auth: SigV4 → Region: `eu-west-2` → leave key/secret blank (uses workspace role)

**OpenSearch (→ logs):**
- Type: OpenSearch
- URL: `https://search-sg-playwright-logs-xxxxxx.eu-west-2.es.amazonaws.com`
- Auth: SigV4 → Service: `es` → Region: `eu-west-2`
- Index: `sg-playwright-logs` — Time field: `@timestamp`

**CloudWatch (→ free EC2 metrics):**
- Type: CloudWatch
- Auth: AWS SDK Default (uses workspace role)
- Default region: `eu-west-2`

### 3.5 IAM — grant AMG workspace access

AMG creates a service role. You need to attach the right policies to it.

In IAM → find the role `AmazonGrafanaServiceRole-xxxxx`:

- For AMP: attach `AmazonPrometheusQueryAccess`
- For CloudWatch: attach `CloudWatchReadOnlyAccess`
- For OpenSearch: add a resource policy on the domain granting the AMG role `es:ESHttpGet`, `es:ESHttpPost`

---

## Step 4 — Summary of environment variables

Set these before running `sg-ec2 create`:

```bash
# Required for metrics → AMP
export AMP_REMOTE_WRITE_URL="https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write"

# Required for logs → OpenSearch
export OPENSEARCH_ENDPOINT="search-sg-playwright-logs-xxxxxx.eu-west-2.es.amazonaws.com"

# Existing (unchanged)
export FAST_API__AUTH__API_KEY__VALUE="your-api-key"
```

If either `AMP_REMOTE_WRITE_URL` or `OPENSEARCH_ENDPOINT` is not set, `provision_ec2.py` will warn during preflight and the corresponding sidecar will run in **local-only mode** (Prometheus stores locally; Fluent Bit writes to stdout). The stack still runs — observability data just won't reach AWS.

---

## Step 5 — Verify shipping is working

**Metrics (AMP):**

```bash
# Check Prometheus remote_write status
sg-ec2 forward-prometheus <deploy-name>
# Open http://localhost:9090/targets — all targets should be UP
# Open http://localhost:9090/status/tsdb — check remote storage queue
```

In AMP console → **Query editor** → try: `up{stack="sg-playwright"}`

**Logs (OpenSearch):**

```bash
# Check Fluent Bit is shipping
sg-ec2 exec <deploy-name> "docker logs sg-playwright-fluent-bit-1 --tail 20"
```

In OpenSearch Dashboards → **Discover** → index `sg-playwright-logs` — logs should appear within ~30s.

**Dashboards (AMG):**

Open AMG workspace → import dashboards from `sgraph_ai_service_playwright/docker/observability/grafana/dashboards/` (once created for AMP/OpenSearch data sources).

---

## Cost estimate (eu-west-2, on-demand)

| Service | Config | $/month (approx) |
|---------|--------|-----------------|
| AMP | ~1M samples/day ingested | ~$2–5 |
| OpenSearch | `t3.small.search` × 1 node | ~$26 |
| AMG | 1 workspace | ~$9 (first 91 days free) |
| **Total** | | **~$37–40/month** |

EC2 (`t3.large`) itself: ~$60/month if running 24/7 — shut down when not in use.
