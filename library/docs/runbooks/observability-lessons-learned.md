# Observability Stack — Lessons Learned (v0.1.69)

**Date:** 2026-04-23  
**Scope:** AMP + OpenSearch + AMG setup for the SG Playwright EC2 stack.

---

## Architecture (what we ended up with)

```
EC2 Instance
├── cadvisor          → container CPU / mem / net / disk
├── node-exporter     → host CPU / mem / disk / net
├── prometheus        → scrapes cadvisor + node-exporter
│                       remote_write → AMP (SigV4, EC2 instance role)
└── fluent-bit        → tails /var/lib/docker/containers/**/*.log
                        ships → OpenSearch (AWS_Auth, EC2 instance role)

AWS Managed Services
├── AMP               → metrics store  → queried by Grafana (AMG)
├── OpenSearch        → log store      → queried by OpenSearch Dashboards
└── AMG (Grafana)     → dashboards for metrics (AMP data source works)
```

**Key decision:** Use **OpenSearch Dashboards** for log exploration, **Grafana** for metrics.  
The Grafana–OpenSearch plugin has compatibility issues with OpenSearch 3.x (see below).

---

## Environment Variables

Set these before running `sp create`:

```bash
# Metrics → AMP
export AMP_REMOTE_WRITE_URL="https://aps-workspaces.eu-west-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write"

# Logs → OpenSearch  (bare hostname — NO https:// prefix)
export OPENSEARCH_ENDPOINT="search-sg-playwright-logs-xxxxx.eu-west-2.es.amazonaws.com"
```

If either is unset, `sp create` warns and the corresponding sidecar falls back to local-only mode
(Prometheus stores locally; Fluent Bit writes to stdout).

---

## IAM — what the `playwright-ec2` role needs

| Policy | Why | How added |
|--------|-----|-----------|
| `AmazonEC2ContainerRegistryReadOnly` | Pull ECR images at boot | `ensure_instance_profile()` |
| `AmazonSSMManagedInstanceCore` | `sp exec` / `sp connect` | `ensure_instance_profile()` |
| `AmazonPrometheusRemoteWriteAccess` | Prometheus → AMP | `ensure_instance_profile()` |
| Inline: `es:ESHttp*` on the domain | Fluent Bit → OpenSearch | Manual (domain-specific, can't be a managed policy) |

**Remove these** if present (legacy, no longer used):
- `AWSXRayDaemonWriteAccess`
- `CloudWatchAgentServerPolicy`

Inline policy JSON for the OpenSearch write permission:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["es:ESHttpPost", "es:ESHttpPut", "es:ESHttpGet", "es:ESHttpHead"],
    "Resource": "arn:aws:es:<region>:<account>:domain/<domain-name>/*"
  }]
}
```

---

## OpenSearch Setup Checklist

1. **Create domain** — OpenSearch 2.x (see compatibility note below). Development tier, public access.

2. **Resource-based policy** — allow `"AWS": "*"` when Fine-Grained Access Control (FGAC) is enabled.  
   FGAC provides the actual security; the resource policy just controls network-level access.

3. **Backend role mapping** (FGAC) — in OpenSearch Dashboards (`/_dashboards`):  
   Security → Roles → `all_access` → Mapped users → Manage mapping → Backend roles:
   - `arn:aws:iam::<account>:role/playwright-ec2` (Fluent Bit writes)
   - `arn:aws:iam::<account>:role/service-role/AmazonGrafanaServiceRole-xxxxx` (Grafana reads)

4. **Create index pattern** in OpenSearch Dashboards:  
   Stack Management → Index Patterns → `sg-playwright-logs` → time field `@timestamp`

---

## Grafana (AMG) Setup

- Use the native **"Amazon Managed Service for Prometheus"** plugin (not generic Prometheus).
- Authentication: **Workspace IAM Role** + region `eu-west-2`.
- AMG workspace role needs `AmazonPrometheusQueryAccess` attached in IAM.

---

## Lessons Learned

### 1. `OPENSEARCH_ENDPOINT` must NOT include `https://`

Fluent Bit's `Host` field takes a bare hostname. Passing `https://search-...` causes a silent
connection failure. Fixed in `render_observability_configs_section()` with `.removeprefix('https://')`.

### 2. OpenSearch 3.x is incompatible with the AMG Grafana plugin

Two separate bugs:
- **`X-Request-Id` validation**: OpenSearch 3.x requires 32 hex chars without dashes; Grafana sends a UUID with dashes.
- **SigV4 service name**: The AMG OpenSearch plugin sends the wrong service name to OpenSearch 3.x.

**Recommendation:** Use OpenSearch **3.x** (3.5 is current) — we use OpenSearch Dashboards natively for logs so the Grafana plugin incompatibilities are irrelevant.  
Only drop to 2.x if you specifically need the Grafana OpenSearch plugin for log queries inside Grafana.

### 3. OpenSearch FGAC needs backend role mapping even with a resource policy

The resource-based policy grants IAM access at the network level. But when FGAC is enabled,
OpenSearch ALSO evaluates its internal role system. An IAM principal must be mapped to an
OpenSearch backend role (`all_access` or similar) to actually read/write data.

Error seen without mapping:
```
"no permissions for [indices:data/write/bulk] and User [name=arn:aws:iam::...:role/playwright-ec2,
backend_roles=[arn:aws:iam::...:role/playwright-ec2], requestedTenant=null]"
```

### 4. OpenSearch Dashboards requires HTTPS from a browser (or the `*` resource policy)

Accessing `/_dashboards` directly from a browser returns:
```
"User: anonymous is not authorized to perform: es:ESHttpGet because no resource-based policy allows"
```

Set resource policy to `"AWS": "*"` — safe when FGAC is enabled, because FGAC gates all data access.

### 5. Fluent Bit `AWS_Auth On` + instance role = zero-credential log shipping

No credentials embedded anywhere. The EC2 instance role provides SigV4 tokens automatically.
The `amazon/aws-for-fluent-bit:stable` image has the OpenSearch output plugin with IAM auth built in.

### 6. Split responsibilities: Grafana for metrics, OpenSearch Dashboards for logs

Grafana's OpenSearch plugin is designed for Elasticsearch and lags behind OpenSearch versions.
OpenSearch Dashboards (the Kibana equivalent) is the native, always-compatible UI for logs.

---

## Verifying the Pipeline

```bash
# Check Fluent Bit is shipping (look for HTTP 200, not 403)
sp logs <name> fluent-bit

# Check Prometheus targets are UP
sp forward-prometheus <name>
# → http://localhost:9090/targets

# Query AMP from Grafana Explore
# → up{stack="sg-playwright"}

# Check OpenSearch has received logs
# → OpenSearch Dashboards → Discover → sg-playwright-logs index pattern
```
