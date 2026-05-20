---
title: SG/Edge — vault targets & Vault Waker
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
scope: the target tier — vault backends (EC2 / Fargate) and the Vault Waker
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__02-edge-fleet.md
---

# Scope

This document covers the vault target tier — the actual EC2 instances or Fargate tasks that run the vault application — and the changes needed in the Vault Waker (existing `sg va` / `sg vp`) for them to work behind the edge.

```
       (SG/Edge fleet)                (this document)
              |                              |
              v                              v
   +------------------+         +-----------------------+
   |   OpenResty      |  -----> |   Vault target        |
   |   proxy          |  HTTP   |   EC2 or Fargate      |
   |                  |  :8080  |   plain HTTP :8080    |
   +------------------+         +-----------------------+
                                          ^
                                          |  provisions
                                          |
                                +-----------------------+
                                |    Vault Waker        |
                                |   (sg va / sg vp,     |
                                |    existing + diffs)  |
                                +-----------------------+
```

Two components: the vault backend (mostly unchanged from today) and the Vault Waker (small additive changes).

# What changes from current state

The good news: the vault target itself barely changes. The Vault Waker gets small additions, not a rewrite.

| Aspect | Today | Behind the edge |
|---|---|---|
| TLS on vault | `letsencrypt-ip` / `letsencrypt-hostname` / `self-signed` cert via cert-init | None. Plain HTTP `:8080`. cert-init container removed from boot path |
| DNS records | A record only: `<slug>.<parent>` -> EC2 public IP | A + TXT: `<slug>.<parent>` -> CloudFront, `_sg.<slug>.<parent>` -> backend metadata |
| Boot time | ~30-90s (EC2) or ~20-30s (Fargate) | Same, minus cert-init overhead (~10-20s saved on EC2) |
| LE rate limits | 50/week per registered domain — the constraint that started this | Gone. No LE involvement at all |
| Vault encryption | Browser AES-GCM, requires HTTPS (secure context) | Same. HTTPS terminates at CF, browser still sees HTTPS |
| Per-vault config | TLS mode + cert-init env | TLS mode dropped from spec; everything else identical |

The cert-init container is the biggest single deletion. `Vault_App__User_Data__Builder` no longer needs to inject ACME credentials, cert paths, FQDN hints, or LE staging flags. The vault simply binds nginx (or whatever serves the vault SPA) to plain HTTP on `:8080`.

# Vault backend internals — EC2 variant

```
+-----------------------------------------------------------------------+
|                      EC2 instance (t3.medium)                         |
|                       <slug>.<parent>.<domain>                        |
|                                                                       |
|   +-----------------------------+   +-----------------------------+   |
|   |       Vault app             |   |     (removed) cert-init     |   |
|   |       nginx :8080           |   |     (removed) cert-renew    |   |
|   |       plain HTTP            |   |                             |   |
|   |                             |   |  No more ACME. No more LE.  |   |
|   |   Serves the vault SPA      |   |  No more :443 binding.      |   |
|   |   browser AES-GCM crypto    |   |                             |   |
|   |   happens in the browser    |   +-----------------------------+   |
|   |   over HTTPS (terminated    |                                     |
|   |   at CF), so secure context |   +-----------------------------+   |
|   |   guarantee holds           |   |       Vault Heartbeat       |   |
|   +-----------------------------+   |     (systemd timer, 60s)    |   |
|              ^                       |                             |   |
|              |                       |  PUTs to a small status     |   |
|              | inbound only          |  endpoint or updates SSM    |   |
|              | from proxy IPs        |  parameter; Vault Waker     |   |
|              | (security group)      |  uses for liveness          |   |
|              |                       +-----------------------------+   |
|   +-----------------------------+                                     |
|   |  IAM instance role          |   +-----------------------------+   |
|   |  - logs:PutLogEvents        |   |          Vector             |   |
|   |  - cloudwatch:PutMetricData |   |     (log shipper)           |   |
|   |  - ssm:UpdateParameter      |   |                             |   |
|   |    (own heartbeat key only) |   |  tails vault app logs       |   |
|   +-----------------------------+   +-----------------------------+   |
|                                                                       |
+-----------------------------------------------------------------------+
                                |
                                | inbound from proxy IPs only
                                | (security group rule)
```

Security group note: the vault's `:8080` should NOT be open to `0.0.0.0/0`. It accepts traffic only from the `SG/Edge` proxy security group. The Vault Waker writes this rule when provisioning; the Edge Waker maintains the proxy SG. This means even if someone learns a vault's public IP, they can't bypass the edge — connections from outside the proxy SG are dropped at the network layer.

# Vault backend internals — Fargate variant

Functionally identical to EC2:

```
+-----------------------------------------------------------------------+
|                       Fargate task (0.5 vCPU)                         |
|                                                                       |
|   +-----------------------------+   +-----------------------------+   |
|   |       Vault app             |   |       Vault Heartbeat       |   |
|   |       nginx :8080           |   |     (in-container or        |   |
|   |       plain HTTP            |   |      out-of-band probe)     |   |
|   +-----------------------------+   +-----------------------------+   |
|                                                                       |
|   Task role: same minimal IAM as EC2 variant                          |
|   Networking: awsvpc mode, security group from SG/Edge proxies only   |
+-----------------------------------------------------------------------+
```

The Fargate path was the original motivator (no cert-init existed for Fargate, hence the brief). Now there's nothing to add — Fargate gets the same plain-HTTP shape as EC2, no special-casing.

# DNS records per slug

Each provisioned slug produces two DNS records, both in the Vault Waker's responsibility:

```
+-------------------------------------------------------------------+
|                  Records written by Vault Waker                   |
+-------------------------------------------------------------------+
|                                                                   |
|  alice.cv.sgraph.ai           A   d123abc.cloudfront.net          |
|     ^ ALIAS to CloudFront      (alias - effectively CNAME for     |
|     ^ TTL 60s                   apex-safe records)                |
|                                                                   |
|                                                                   |
|  _sg.alice.cv.sgraph.ai       TXT  "v=1;ip=10.0.1.5;port=8080;    |
|     ^ The routing record           type=ec2;launched=1747700000;  |
|     ^ TTL 30s                      instance=i-0abc123def"         |
|     ^ Read by OpenResty                                           |
|                                                                   |
+-------------------------------------------------------------------+
```

A record is what the browser uses. TXT is what OpenResty uses. They serve different lookups; both must exist for the slug to function.

## TXT record schema

Version-prefixed to allow evolution. v=1 fields:

| Field | Required | Format | Example | Purpose |
|---|---|---|---|---|
| `v` | yes | integer | `1` | schema version |
| `ip` | yes | IPv4 | `10.0.1.5` | backend address |
| `port` | yes | uint16 | `8080` | backend port |
| `type` | yes | enum | `ec2` / `fargate` | informational, lets proxy adjust behavior if needed |
| `launched` | yes | unix ts | `1747700000` | for staleness detection |
| `instance` | no | string | `i-0abc123def` | for ops, not used by proxy |

Parsing: simple `key=value;key=value` format. Stays under DNS TXT 255-char limit. Resist the temptation to put JSON in there — it works but is harder to debug from `dig` output.

# Slug state machine

Slugs have four lifecycle states. Only the Vault Waker can transition them.

```
       +-----------------+
       |  unprovisioned  |  <-- no DNS records exist
       +-----------------+
              |
              | sg va <slug>  /  sg vp <slug>
              v
       +-----------------+
       |   provisioning  |  <-- backend booting, no DNS yet
       +-----------------+
              |
              | backend healthy +
              | DNS records written
              v
       +-----------------+    idle (no req for X min)
       |     active      |  -------------------------+
       +-----------------+                           |
              ^                                      v
              | first request               +----------------+
              | wakes it                    |     stopped    |
              |                             | (EC2 only)     |
              +-----------------------------|                |
                                            +----------------+
                                                   |
                                                   | sg va terminate
                                                   v
                                            (unprovisioned)
```

The active <-> stopped transition is the EC2 wake-on-access pattern from `sg vp`. Fargate doesn't have a "stopped" state — tasks are running or terminated. For Fargate slugs, the state machine collapses to {unprovisioned, provisioning, active, terminated}.

# Cold-vault sequence (waking a stopped EC2 vault)

This is the *second* layer of cold start, distinct from the cold-cold proxy fleet boot covered in doc 2.

```
User    Proxy (OpenResty)    Vault Waker     EC2 API     Route 53
 |             |                  |              |           |
 |---req------>|                  |              |           |
 |             |                  |              |           |
 |             | TXT lookup       |              |           |
 |             | returns          |              |           |
 |             | ip=10.0.1.5      |              |           |
 |             |                  |              |           |
 |             |---attempt------->X (conn refused, EC2 stopped)
 |             |                  |              |           |
 |             | invalidate cache |              |           |
 |             | for this slug    |              |           |
 |             |                  |              |           |
 |             |---trigger-------->|             |           |
 |             |   (async HTTP    |              |           |
 |             |    to waker fn   |              |           |
 |             |    URL)          |              |           |
 |             |                  |              |           |
 |<-loading----|                  |              |           |
 | page        |                  |              |           |
 |             |                  |--StartInstances->        |
 |             |                  |              |           |
 |             |                  | (poll EC2 status)        |
 |             |                  |              |           |
 |        ...30-90s wake time...                             |
 |             |                  |              |           |
 |             |                  |<-running-----|           |
 |             |                  |                          |
 |             |                  | (get new IP, may differ) |
 |             |                  |                          |
 |             |                  |--update TXT record------>|
 |             |                  |  (new ip, new launched)  |
 |             |                  |<-ok----------------------|
 |             |                  |                          |
 |   (client polls /status, eventually retries original URL) |
 |<------- (warm path now works) -------------------------> |
```

Two important things in this flow:

1. **The TXT record gets updated on wake** because EC2 instance public IPs can change across stop/start. The Vault Waker re-writes TXT (same key, new values) as the last step before reporting ready.
2. **The proxy invalidates its cache eagerly** on connection failure. This is critical — if the proxy held a stale IP for 30s after wake-up, the user would see continued failures.

For Fargate the wake-on-access flow doesn't apply (no stopped state). Slugs are either running or gone. The same loading page logic kicks in when the slug truly doesn't exist (404 → optional "provision a new vault here?" page), but there's no resurrection.

# Cleanup and orphan handling

The architecture's weakest point is orphaned DNS records — slugs whose backends are gone but whose DNS records remain. Three places where this can happen:

| Failure | Symptom | Mitigation |
|---|---|---|
| Vault Waker crashes mid-provision | Backend running but DNS not written | Vault Waker writes DNS first thing on success, or rolls back backend if DNS write fails |
| Vault Waker crashes mid-terminate | DNS exists but backend gone | Periodic reaper job (covered below) |
| EC2 / Fargate dies unexpectedly | Backend gone, DNS stale, Vault Heartbeat stops | Reaper detects via heartbeat staleness |

The reaper is a scheduled Lambda (separate from Vault Waker; let's call it `Vault_Reaper`) that runs every 5 minutes:

```
+---------------------------------------------------------------+
|                         Vault Reaper                          |
+---------------------------------------------------------------+
|                                                               |
|  Every 5 minutes:                                             |
|                                                               |
|  1. List all _sg.* TXT records in managed zones               |
|  2. For each record:                                          |
|       a. Parse TXT, get instance/task identifier              |
|       b. Check EC2/Fargate API for state                      |
|       c. Check last_heartbeat from SSM Parameter Store        |
|       d. If state == terminated OR                            |
|          heartbeat older than 10 minutes OR                   |
|          launched-but-never-heartbeat > 5 min:                |
|             remove _sg.<slug> TXT and <slug> A records         |
|             remove SSM heartbeat parameter                    |
|             log + emit metric                                 |
|                                                               |
+---------------------------------------------------------------+
```

The reaper is conservative — false negatives (failing to reap an orphan) are fine, false positives (reaping a live vault) are damaging. Hence the redundant signals (instance state + heartbeat age) and the multi-minute hysteresis.

# IAM model

The Vault Waker needs slightly different permissions than today:

```
+-------------------------------------------------------------+
|                  Vault Waker IAM (additions)                |
+-------------------------------------------------------------+
|  EXISTING:                                                  |
|    - ec2:RunInstances, ec2:TerminateInstances               |
|    - ec2:DescribeInstances                                  |
|    - ec2:StartInstances, ec2:StopInstances (wake)           |
|    - ecs:RunTask, ecs:StopTask (Fargate)                    |
|    - iam:PassRole (vault instance role)                     |
|    - route53:ChangeResourceRecordSets (slug zones)          |
|                                                             |
|  NEW (small additions):                                     |
|    - route53:ChangeResourceRecordSets (_sg.* records too)   |
|    - ssm:PutParameter, ssm:GetParameter                     |
|      (for heartbeat coordination)                           |
|                                                             |
|  REMOVED (the cert-init permissions go away):               |
|    - acm:* (was unused if cert-init owned the cert)          |
|    - secretsmanager:GetSecretValue (LE account)             |
+-------------------------------------------------------------+
```

The Vault Waker continues to have no edge permissions — it can't modify `proxies.<parent>` records or touch the Edge Waker's resources. The blast-radius separation is symmetric.

The vault instance role itself is smaller than today (no ACM, no Secrets Manager for cert key, no Route 53 — those were either unused or moved to Vault Waker).

# Changes to existing modules

For an implementing engineer working from the existing `sg_compute_specs/` tree:

| File | Change |
|---|---|
| `vault_app/service/Vault_App__Service.py` | Remove `tls_mode` parameter from `create_stack`. Always plain HTTP. Add TXT record write to the readiness gate |
| `vault_app/service/Vault_App__User_Data__Builder.py` | Remove cert-init container env injection. Remove ACME credentials. Remove FQDN propagation logic |
| `vault_publish/service/Vault_Publish__Service.py` | Remove `tls_mode=letsencrypt-hostname` path. Slug registration now writes A + TXT pointing at CloudFront, not direct to EC2 |
| `vault_app/fargate/service/Vault_App__Fargate__Setup.py` | Remove the TLS-gap note. This is now the canonical Fargate flow |
| `vault_app/service/Vault_App__Auto_DNS.py` | Add TXT record writing alongside A. Remove the "wait for DNS before cert-init" coordination |
| (new) `edge/service/SG_Edge__TXT_Builder.py` | Helper to compose and validate v=1 TXT records, shared between Vault Waker and Vault Reaper |
| (new) `vault_reaper/service/Vault_Reaper__Service.py` | The scheduled reaper |

Total deletion vs addition is roughly balanced — net code surface is similar. The complexity reduction is in the *boot path* (cert-init container, ACME, FQDN coordination all gone) which is where most of the operational pain lives today.

# Open questions

1. **Heartbeat storage.** SSM Parameter Store is convenient but has rate limits. At 500 concurrent vaults heartbeating every 60s, that's ~8 PUTs/s, well under the SSM throttle. At 10k it would be problematic. Worth re-evaluating storage choice if scaling targets grow. Cheap alternative: just rely on EC2/Fargate API state (no heartbeat at all), accept slightly slower orphan detection.
2. **Backend auth between proxy and target.** Currently the security group enforces "only proxies can reach target." Should we add HTTP-level auth too (mTLS, shared secret, signed header)? Defense in depth, but adds complexity. Recommend deferring to v2 — security group is good enough for MVP.
3. **Fargate task IP discovery timing.** Fargate tasks expose their IP in the task description, but only after the task transitions to RUNNING. The Vault Waker must poll DescribeTasks until IP is available, then write TXT. Adds ~5-10s to provisioning. Acceptable, but worth optimizing if Fargate becomes the primary path.
4. **What about WebSockets?** Vault currently doesn't use WS but might in future (live collab). The edge fully supports WS (OpenResty handles `Upgrade` natively), CF supports WS, the architecture works without changes. Worth confirming in MVP testing.
